from flask import Flask, render_template, request, redirect, url_for, jsonify
from flask_sqlalchemy import SQLAlchemy
from datetime import datetime, timezone

# INITIALIZING THE CODE.
app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'postgresql://postgres:srij%40%40post@localhost:5432/test'
db = SQLAlchemy(app)

class Todo(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content = db.Column(db.String(200), nullable=False)
    taskcategory = db.Column(db.String(256))
    completed = db.Column(db.Integer, default=0)
    date_created = db.Column(db.DateTime, default=datetime.now(timezone.utc))

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
        per_page = request.args.get("per_page", 7, type=int)

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
            query = query.order_by(Todo.date_created.desc())

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

if __name__ == "__main__":
    app.run(debug=True, host="0.0.0.0", port=5678)
