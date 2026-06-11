from tkinter import *
from tkinter import messagebox
from tkinter import ttk
import sqlite3
from datetime import datetime, date
from tkcalendar import DateEntry
from plyer import notification
import plyer.platforms.win.notification
import csv
import os
import sys

def resource_path(relative_path):
    try:
        base_path = sys._MEIPASS
    except Exception:
        base_path = os.path.abspath(".")
    return os.path.join(base_path, relative_path)

# ---------------- UI ----------------
selected_task_id = None

PRIMARY = "#3498DB"
SUCCESS = "#2ECC71"
DANGER = "#E74C3C"
BG = "#1E1E1E"
CARD = "#2C2C2C"
TEXT = "#FFFFFF"

root = Tk()

icon_path = resource_path("icon.ico")

if os.path.exists(icon_path):
    try:
        root.iconbitmap(icon_path)
    except:
        pass

root.title("Task Manager")
root.geometry("900x790")
root.resizable(True, True)

BG = "#1e1e2f"
FG = "#ffffff"
BTN_ADD = "#4CAF50"

root.configure(bg=BG)

# ---------------- DATABASE ----------------
import os
import sys
import sqlite3

def get_db_path():
    # Always use project folder OR exe folder consistently
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))

    return os.path.join(base_dir, "tasks.db")

DB_PATH = get_db_path()

conn = sqlite3.connect(DB_PATH, timeout=10)
cursor = conn.cursor()

cursor.execute("""
CREATE TABLE IF NOT EXISTS tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task TEXT NOT NULL,
    completed INTEGER DEFAULT 0,
    priority TEXT DEFAULT 'MEDIUM',
    due_date TEXT,
    category TEXT DEFAULT 'Personal'
)
""")
conn.commit()

try:
    cursor.execute(
        "ALTER TABLE tasks ADD COLUMN category TEXT DEFAULT 'Personal'"
    )
    conn.commit()
except:
    pass

task_ids = []
current_filter = "ALL"
# ---------------- HELPERS ----------------
def parse_date(d):

    try:

        # empty check
        if not d:
            return None

        # convert to string + remove spaces
        d = str(d).strip()

        # ignore placeholder
        if d == "DD-MM-YYYY":
            return None

        # convert / into -
        d = d.replace("/", "-")

        # split date
        parts = d.split("-")

        # must contain 3 parts
        if len(parts) != 3:
            return None

        # auto-fix single digits
        day = parts[0].zfill(2)
        month = parts[1].zfill(2)
        year = parts[2]

        # rebuild proper format
        fixed_date = f"{day}-{month}-{year}"

        # convert to date object
        return datetime.strptime(
            fixed_date,
            "%d-%m-%Y"
        ).date()

    except Exception as e:

        print("DATE ERROR:", d, e)

        return None
    

def update_counter():
    if 'stats_label' not in globals():
        return
    cursor.execute(
        "SELECT completed, due_date FROM tasks"
    )

    tasks = cursor.fetchall()

    total = len(tasks)
    completed = 0
    pending = 0
    overdue = 0

    for completed_status, due_date in tasks:

        d = parse_date(due_date)

        if completed_status == 1:
            completed += 1

        else:
            pending += 1

            if d is not None and d < date.today():
                overdue += 1

    stats_label.config(
        text=
        f"Total: {total}    "
        f"Pending: {pending}    "
        f"Completed: {completed}    "
        f"Overdue: {overdue}"
    )
    if total > 0:
     percent = int((completed / total) * 100)
    else:
     percent = 0

    progress["value"] = percent
    progress_label.config(text=f"Progress: {percent}%")

def update_category_stats():
    if 'category_stats_label' not in globals():
        return
    cursor.execute(
        """
        SELECT category, COUNT(*)
        FROM tasks
        GROUP BY category
        """
    )

    data = cursor.fetchall()

    text = ""

    for category, count in data:

        text += f"{category}: {count}   "

    category_stats_label.config(text=text)

# ---------------- CORE FUNCTIONS ----------------
def add_task(event=None):
    task = entry.get().strip()
    priority = priority_var.get()
    category = category_var.get()
    due_date = due_entry.get_date().strftime("%d-%m-%Y")

    if not task:
        return

    cursor.execute(
      """
      INSERT INTO tasks
      (task, completed, priority, due_date, category)
      VALUES (?, ?, ?, ?, ?)
      """,
      (task, 0, priority, due_date, category)
    )
    conn.commit()

    entry.delete(0, END)
    refresh()


def delete_task():

    global selected_task_id

    if selected_task_id is None:
        return

    cursor.execute(
        "SELECT task FROM tasks WHERE id=?",
        (selected_task_id,)
    )

    result = cursor.fetchone()

    if not result:
        return

    task_name = result[0]

    answer = messagebox.askyesno(
        "Delete Task",
        f"Delete '{task_name}' ?"
    )

    if answer:
        cursor.execute(
            "DELETE FROM tasks WHERE id=?",
            (selected_task_id,)
        )

        conn.commit()

        selected_task_id = None   # ⭐ IMPORTANT
        entry.delete(0, END)      # ⭐ optional cleanup

        refresh()

def clear_completed_tasks():

    answer = messagebox.askyesno(
        "Clear Completed Tasks",
        "Delete all completed tasks?"
    )

    if not answer:
        return

    cursor.execute(
        "DELETE FROM tasks WHERE completed=1"
    )

    conn.commit()
    refresh()


def complete_task():
    
    global selected_task_id

    if selected_task_id is None:
        return

    cursor.execute(
        "UPDATE tasks SET completed=1 WHERE id=?",
        (selected_task_id,)
    )

    conn.commit()
    selected_task_id = None
    refresh()

def mark_pending():

    global selected_task_id

    if selected_task_id is None:
        return

    cursor.execute(
        "UPDATE tasks SET completed=0 WHERE id=?",
        (selected_task_id,)
    )

    conn.commit()
    selected_task_id = None
    refresh()


def edit_task():

    global selected_task_id

    if selected_task_id is None:
        return

    new_task = entry.get().strip()

    if not new_task:
        return

    new_priority = priority_var.get()
    new_category = category_var.get()
    new_due_date = due_entry.get_date().strftime("%d-%m-%Y")

    cursor.execute(
        """
        UPDATE tasks
        SET task=?,
            priority=?,
            category=?,
            due_date=?
        WHERE id=?
        """,
        (
            new_task,
            new_priority,
            new_category,
            new_due_date,
            selected_task_id
        )
    )

    conn.commit()

    entry.delete(0, END)


    selected_task_id = None

    refresh()


def search_task():
    query = search_entry.get().lower()

    cursor.execute("SELECT id, task, completed, priority, due_date, category FROM tasks")
    tasks = cursor.fetchall()

    for item in tree.get_children():
        tree.delete(item)

    for task_id, task, completed, priority, due_date, category in tasks:

        if (
            query in task.lower()
            or query in priority.lower()
            or query in category.lower()
            or query in str(due_date).lower()
        ):

            status = "✓ Done" if completed == 1 else "Pending"

            tag = "completed" if completed == 1 else "pending"

            tree.insert(
              "",
              "end",
              iid=task_id,
              values=(
               status,
               category,
               priority,
               task,
               due_date
              ),
              tags=(tag,)
            )


def on_select(event):

    global selected_task_id

    selected = tree.focus()   # ⭐ MORE RELIABLE THAN selection()

    if not selected:
        return

    values = tree.item(selected, "values")

    if not values:
        return

    status = values[0]
    category = values[1]
    priority = values[2]
    task = values[3]
    due_date = values[4]

    selected_task_id = int(selected)

    # ✅ AUTO FILL ENTRY
    entry.delete(0, END)
    entry.insert(0, task)

    priority_var.set(priority)
    category_var.set(category)

    if due_date and due_date != "None":
        try:
            due_entry.set_date(
                datetime.strptime(due_date, "%d-%m-%Y")
            )
        except:
            pass
   
      
def show_all():
    search_entry.delete(0, END)
    global current_filter
    current_filter = "ALL"
    refresh()

def show_all_tasks():
    global current_filter
    current_filter = "ALL"
    refresh()

def show_pending_tasks():
    global current_filter
    current_filter = "PENDING"
    refresh()

def show_completed_tasks():
    global current_filter
    current_filter = "COMPLETED"
    refresh()

def show_overdue_tasks():
    global current_filter
    current_filter = "OVERDUE"
    refresh()

def desktop_notification():

    cursor.execute(
        "SELECT task, due_date, completed FROM tasks"
    )

    tasks = cursor.fetchall()

    today_count = 0
    overdue_count = 0

    for task, due_date, completed in tasks:

        if completed == 1:
            continue

        d = parse_date(due_date)

        if d is None:
            continue

        if d == date.today():
            today_count += 1

        elif d < date.today():
            overdue_count += 1

    if today_count == 0 and overdue_count == 0:
        return

    try:
        notification.notify(
            title="Task Manager",
            message=
            f"Due Today: {today_count}\n"
            f"Overdue: {overdue_count}",
            timeout=10
        )
    except Exception as e:
        print("Notification Error:", e)


def auto_notification():

    try:
        desktop_notification()
    except:
        pass

    root.after(
        10800000,
        auto_notification
    )


def export_csv():

    cursor.execute(
        """
        SELECT
        task,
        priority,
        category,
        due_date,
        completed
        FROM tasks
        """
    )

    tasks = cursor.fetchall()

    with open(
        "tasks_export.csv",
        "w",
        newline="",
        encoding="utf-8"
    ) as file:

        writer = csv.writer(file)

        writer.writerow(
            [
                "Task",
                "Priority",
                "Category",
                "Due Date",
                "Completed"
            ]
        )

        for task, priority, category, due_date, completed in tasks:

            writer.writerow(
                [
                    task,
                    priority,
                    category,
                    due_date,
                    "Yes" if completed else "No"
                ]
            )

    messagebox.showinfo(
        "Export Successful",
        "Tasks exported to tasks_export.csv"
    )

# ---------------- REFRESH (SORTING FIXED) ----------------
def refresh():

    cursor.execute(
        "SELECT id, task, completed, priority, due_date, category FROM tasks"
    )

    tasks = cursor.fetchall()

    # ---------- FILTER ----------
    filtered_tasks = []

    for task in tasks:

        task_id, task_name, completed, priority, due_date, category = task
        d = parse_date(due_date)

        if current_filter == "ALL":
            filtered_tasks.append(task)

        elif current_filter == "PENDING" and completed == 0:
            filtered_tasks.append(task)

        elif current_filter == "COMPLETED" and completed == 1:
            filtered_tasks.append(task)

        elif (
            current_filter == "OVERDUE"
            and completed == 0
            and d is not None
            and d < date.today()
        ):
            filtered_tasks.append(task)

    tasks = filtered_tasks

    # ---------- SORT ----------
    def sort_key(x):

        task_id, task, completed, priority, due_date, category = x
        d = parse_date(due_date)

        # 1. completed always last
        if completed == 1:
            return (2, date.max)

        # 2. no date goes middle
        if d is None:
            return (1, date.max)

        # 3. sort by date
        return (0, d)

    tasks.sort(key=sort_key)

    # ---------- CLEAR TREE ----------
    for item in tree.get_children():
        tree.delete(item)

    task_ids.clear()

    # ---------- DISPLAY ----------
    for task_id, task, completed, priority, due_date, category in tasks:

        d = parse_date(due_date)

        status = "✓ Done" if completed == 1 else "Pending"

        # tags (colors)
        if completed == 1:
            tag = "completed"
        elif d is not None and d < date.today():
            tag = "overdue"
        elif d is not None and d == date.today():
            tag = "today"
        else:
            tag = "pending"

        tree.insert(
            "",
            "end",
            iid=task_id,
            values=(status, category, priority, task, due_date),
            tags=(tag,)
        )

    # ---------- UPDATE UI ----------
    update_counter()
    update_category_stats()
# ---------------- UI ----------------
Label(
    root,
    text="TASK MANAGER",
    font=("Segoe UI", 18, "bold"),
    bg=BG,
    fg=TEXT
).pack(pady=15)

input_frame = Frame(root, bg=BG)
input_frame.pack(pady=10)

options_frame = Frame(root, bg=BG)
options_frame.pack(pady=5)


entry = Entry(input_frame,width=35,
    font=("Segoe UI", 11))
entry.grid(row=0, column=0, padx=5)

add_btn = Button(input_frame, text="Add Task",width=9,height=1,bg=SUCCESS,fg=TEXT,font=("Segoe UI", 11, "bold"),command=add_task)
add_btn.grid(row=0, column=1, padx=5)

edit_btn = Button(
    input_frame,
    text="Edit",
    width=9,
    height=1,
    bg="grey",
    fg=TEXT,
    font=("Segoe UI", 11, "bold"),
    command=edit_task
)

edit_btn.grid(
    row=0,
    column=2,
    padx=5
)

entry.bind("<Return>", add_task)

style = ttk.Style()

style.theme_use("clam")


style.configure(
    "Treeview",
    background="#2C2C2C",
    foreground="white",
    fieldbackground="#2C2C2C",
    rowheight=28,
    font=("Segoe UI", 11)
)

style.configure(
    "Treeview.Heading",
    font=("Segoe UI", 11, "bold")
)

style.map(
    "Treeview",
    background=[("selected", "#3498DB")]
)
priority_var = StringVar(value="MEDIUM")

priority_combo = ttk.Combobox(
    options_frame,
    textvariable=priority_var,
    values=["HIGH", "MEDIUM", "LOW"],
    state="readonly",
    style="Dark.TCombobox",
    font=("Segoe UI", 11),
    width=16
)

priority_combo.grid(
    row=0,
    column=0,
    padx=10,
    pady=5
)


category_var = StringVar(value="Personal")

category_combo = ttk.Combobox(
    options_frame,
    textvariable=category_var,
    values=[
        "Study",
        "Work",
        "Personal",
        "Shopping",
        "Other"
    ],
    state="readonly",
    style="Dark.TCombobox",
    font=("Segoe UI", 11),
    width=16
)

category_combo.grid(
    row=0,
    column=1,
    padx=10,
    pady=5
)


due_entry = DateEntry(
    options_frame,
    width=16,
    font=("Segoe UI", 11),
    background="darkblue",
    foreground="white",
    borderwidth=2,
    date_pattern="dd-mm-yyyy"
)

due_entry.grid(
    row=0,
    column=2,
    padx=10,
    pady=5
)
# ---------------- SEARCH ----------------
search_frame = Frame(root, bg=BG)
search_frame.pack(pady=5)

search_entry = Entry(
    search_frame,
    width=35,
    font=("Segoe UI", 11)
)
search_entry.grid(row=0, column=0, padx=5)

search_entry.bind(
    "<Return>",
    lambda event: search_task()
)

Button(
    search_frame,
    text="Search",
    command=search_task,
    #bg="grey",
    #fg="white",
    width=9,height=1,font=("Segoe UI", 11, "bold")
).grid(row=0, column=1, padx=5)

Button(
    search_frame,
    text="Show All",
    command=show_all,
    #bg="grey",
    #fg="white",
    width=9,height=1,font=("Segoe UI", 11, "bold")
).grid(row=0, column=2, padx=5)


# ---------------- FILTERS ----------------
filter_frame = Frame(root, bg=BG)
filter_frame.pack(pady=9)


Button(filter_frame, text="All",
       command=show_all_tasks,
       #bg="grey",
       #fg="white",
       width=9,font=("Segoe UI", 10, "bold")).grid(row=0, column=0, padx=3)

Button(filter_frame, text="Pending",
       command=show_pending_tasks,
       #bg="grey",
       #fg="white",
       width=9,font=("Segoe UI", 10, "bold")).grid(row=0, column=2, padx=3)

Button(filter_frame, text="Completed",
       command=show_completed_tasks,
       #bg="grey",
       #fg="white",
       width=9,font=("Segoe UI", 10, "bold")).grid(row=0, column=3, padx=3)

Button(filter_frame, text="Overdue",
       command=show_overdue_tasks,
       #bg="grey",
       #fg="white",
       width=9,font=("Segoe UI", 10, "bold")).grid(row=0, column=1, padx=3)


# ---------------- tree creation ----------------

Label(
    root,
    text="Task List",
    bg=BG,
    fg="white",
    font=("Segoe UI", 12, "bold")
).pack(pady=(5,0))
frame = Frame(root, bg="#2b2b3c",bd=0)
frame.pack(pady=0)

scrollbar = Scrollbar(frame)
scrollbar.pack(side=RIGHT, fill=Y)


tree = ttk.Treeview(
    frame,
    columns=("Status","Category", "Priority", "Task", "Due"),
    show="headings",height=10,
    yscrollcommand=scrollbar.set
)
tree.configure(cursor="hand2")
tree.bind("<<TreeviewSelect>>", on_select)

tree.tag_configure("completed", foreground="grey")
tree.tag_configure("today", foreground="orange")
tree.tag_configure("overdue", foreground="#FF6B6B")

tree.heading("Status", text="Status")
tree.heading("Category", text="Category")
tree.heading("Priority", text="Priority")
tree.heading("Task", text="Task")
tree.heading("Due", text="Due Date")

tree.column("Status", width=90, anchor="center")
tree.column("Category", width=120, anchor="center")
tree.column("Priority", width=100, anchor="center")
tree.column("Task", width=450,anchor="center")
tree.column("Due", width=120, anchor="center")

tree.pack(fill=BOTH, expand=True)

scrollbar.config(command=tree.yview)
tree.bind("<<TreeviewSelect>>", on_select)

# ---------------- BUTTONS ----------------
action_frame = Frame(root, bg=BG)
action_frame.pack(pady=10)

Button(
    action_frame,
    text="Clear Done",
    command=clear_completed_tasks,
    #bg="white",
    #fg="white",
    width=10,
    font=("Segoe UI", 10, "bold")
).grid(row=0, column=3, padx=5)

Button(
    action_frame,
    text="Complete",
    command=complete_task,
    bg="#27AE60",
    fg="white",
    width=10,font=("Segoe UI", 10, "bold")
).grid(row=0, column=1, padx=5)

Button(
    action_frame,
    text="Delete",
    command=delete_task,
    bg=DANGER,
    fg="white",
    width=10,font=("Segoe UI", 10, "bold")
).grid(row=0, column=5, padx=5)

Button(
    action_frame,
    text="Pending",
    command=mark_pending,
    #bg="grey",
    #fg="white",
    width=10,
    font=("Segoe UI", 10, "bold")
).grid(row=0, column=2, padx=5)

Button(
    action_frame,
    text="Export",
    command=export_csv,
   # bg="grey",
   # fg="white",
    width=10,
    font=("Segoe UI", 10, "bold")
).grid(row=0, column=4, padx=5)

stats_label = Label(
    root,
    text="",
    bg=BG,
    fg=TEXT,
    font=("Segoe UI", 10, "bold")
)

stats_label.pack(pady=10)

category_stats_label = Label(
    root,
    text="",
    bg=BG,
    fg=TEXT,
    font=("Segoe UI", 10)
)

category_stats_label.pack()

progress_frame = Frame(root, bg=BG)
progress_frame.pack(pady=10)

progress = ttk.Progressbar(
    progress_frame,
    orient="horizontal",
    length=300,
    mode="determinate"
)
progress.pack(side=LEFT, padx=10)

progress_label = Label(
    progress_frame,
    text="Progress: 0%",
    bg=BG,
    fg=TEXT,
    font=("Segoe UI", 10, "bold")
)
progress_label.pack(side=LEFT)

refresh()
update_counter()
update_category_stats()
auto_notification()

root.mainloop()