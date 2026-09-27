"""
cli.py
------
This is the "presentation" layer — today, a text menu in your terminal.
In Phase 3, this file gets REPLACED by a web UI, but service.py
underneath won't need to change. That's the payoff of separating layers
now, even though it feels like overkill for such a small app.

Rule this file follows: cli.py never imports storage.py or touches a
Task's internals directly for data changes — it only calls service.py.
"""

import service


def print_menu():
    print("\n=== TaskPilot ===")
    print("1. Add task/habit")
    print("2. List all")
    print("3. Mark complete")
    print("4. Delete")
    print("5. Weekly stats")
    print("6. Quit")


def handle_add():
    name = input("Name: ").strip()
    kind = input("Type ('task' or 'habit', default 'task'): ").strip() or "task"
    if kind not in ("task", "habit"):
        print("Invalid type, defaulting to 'task'.")
        kind = "task"
    task = service.add_task(name, kind)
    print(f"Added: [{task.id}] {task.name} ({task.kind})")


def handle_list():
    tasks = service.get_all_tasks()
    if not tasks:
        print("No tasks yet. Add one!")
        return
    for t in tasks:
        status = "✓ done today" if t.is_completed_today() else "pending"
        streak = f", streak: {t.current_streak()}" if t.kind == "habit" else ""
        print(f"[{t.id}] {t.name} ({t.kind}) - {status}{streak}")


def handle_complete():
    handle_list()
    try:
        task_id = int(input("Task ID to mark complete: "))
    except ValueError:
        print("Please enter a number.")
        return
    task = service.complete_task(task_id)
    if task:
        print(f"Marked '{task.name}' complete for today.")
    else:
        print("No task with that ID.")


def handle_delete():
    handle_list()
    try:
        task_id = int(input("Task ID to delete: "))
    except ValueError:
        print("Please enter a number.")
        return
    if service.delete_task(task_id):
        print("Deleted.")
    else:
        print("No task with that ID.")


def handle_stats():
    rate = service.weekly_completion_rate()
    print(f"Weekly completion rate: {rate}%")


def run():
    actions = {
        "1": handle_add,
        "2": handle_list,
        "3": handle_complete,
        "4": handle_delete,
        "5": handle_stats,
    }
    while True:
        print_menu()
        choice = input("Choose an option: ").strip()
        if choice == "6":
            print("Goodbye!")
            break
        action = actions.get(choice)
        if action:
            action()
        else:
            print("Invalid option, try again.")


if __name__ == "__main__":
    run()
