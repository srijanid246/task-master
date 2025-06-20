from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone
from dotenv import load_dotenv
import os

load_dotenv()

# INITIALIZING THE APP
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('DATABASE_URL')
db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    taskcategory = db.Column(db.String(256))
    completed = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.now(timezone.utc))
    order = db.Column(db.Integer, default=0) 

    def __repr__(self):
        return f"<Task {self.id}>"

with app.app_context():
    db.create_all()

@app.route("/", methods=["GET", "POST"])
def index():
    if request.method == "POST":
        task_content = request.form["content"].strip()
        task_category = request.form.get("taskcategory", "").strip()
        if not task_content:
            return "Task content cannot be empty."
        new_task = Todo(
            content=task_content,
            taskcategory=task_category,
            date_created=datetime.now(timezone.utc)
        )
        try:
            db.session.add(new_task)
            db.session.commit()
            return redirect(url_for("index"))
        except Exception as e:
            return f"There was an issue adding your task: {str(e)}"
    else:
        sort = request.args.get("sort", "default")
        by = request.args.get("by", "content")
        page = request.args.get("page", 1, type=int)
        per_page = 7
        query = Todo.query
        if sort == "asc" and by == "content":
            query = query.order_by(Todo.content.asc())
        elif sort == "desc" and by == "content":
            query = query.order_by(Todo.content.desc())
        elif sort == "asc" and by == "date":
            query = query.order_by(Todo.date_created.asc())
        elif sort == "desc" and by == "date":
            query = query.order_by(Todo.date_created.desc())
        else:
            query = query.order_by(Todo.order.asc())
        pagination = query.paginate(page=page, per_page=per_page, error_out=False)
        tasks = pagination.items
        return render_template("index.html", tasklist=tasks, sort=sort, by=by, pagination=pagination)

@app.route("/update_task/<int:id>", methods=["POST"])
def update_task(id):
    task = Todo.query.get_or_404(id)
    data = request.get_json()
    content = data.get("content", "").strip()
    if content:
        task.content = content
        db.session.commit()
        return jsonify({"success": True, "new_content": content})
    return jsonify({"success": False, "error": "Content cannot be empty."})

@app.route("/batch_update", methods=["POST"])
def batch_update():
    data = request.get_json()
    updates = data.get("updates", [])

    updated = []
    for item in updates:
        task = Todo.query.get(item["id"])
        if task:
            task.content = item["content"]
            updated.append({"id": task.id, "content": task.content})
    db.session.commit()
    return jsonify({"success": True, "updated": updated})


@app.route("/delete_task/<int:id>", methods=["POST"])
def delete_task(id):
    task = Todo.query.get(id)
    if not task:
        return jsonify({"already_deleted": True})
    try:
        db.session.delete(task)
        db.session.commit()
        return jsonify({"success": True})
    except Exception as e:
        return jsonify({"success": False, "error": str(e)})

@app.route("/reorder_tasks", methods=["POST"])
def reorder_tasks():
    data = request.get_json()
    dragged_id = data.get("dragged_id")
    target_id = data.get("target_id")

    dragged = Todo.query.get(dragged_id)
    target = Todo.query.get(target_id)

    if not dragged or not target:
        return jsonify({"success": False, "error": "Invalid task IDs"})

    all_tasks = Todo.query.order_by(Todo.order.asc()).all()
    task_list = [t for t in all_tasks if t.id != dragged.id]

    target_index = next((i for i, t in enumerate(task_list) if t.id == target.id), None)
    if target_index is None:
        return jsonify({"success": False, "error": "Target not found"})

    task_list.insert(target_index, dragged)

    for idx, task in enumerate(task_list):
        task.order = idx

    db.session.commit()
    return jsonify({"success": True})


@app.route("/replace_task_field", methods=["POST"])
def replace_task_field():
    data = request.get_json()
    source_id = data.get("source_id")
    target_id = data.get("target_id")
    field = data.get("field")

    source = Todo.query.get(source_id)
    target = Todo.query.get(target_id)

    if not source or not target or field not in ["content", "date", "time"]:
        return jsonify({"success": False, "error": "Invalid input"})

    if field == "content":
        target.content = source.content
    elif field == "date":
        target.date_created = datetime.combine(
            source.date_created.date(),
            target.date_created.time(),
            tzinfo=target.date_created.tzinfo
        )
    elif field == "time":
        target.date_created = datetime.combine(
            target.date_created.date(),
            source.date_created.time(),
            tzinfo=target.date_created.tzinfo
        )
    db.session.commit()
    return jsonify({"success": True})

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5678)