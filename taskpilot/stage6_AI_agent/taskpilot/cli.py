"""
cli.py
------
Phase 4 update: the CLI now requires login too, using the SAME auth.py
and service.py the web API uses — no HTTP involved here, since cli.py
calls these as plain Python function calls in the same process. This is
a nice demonstration that auth logic lives in its own layer, reusable
by any presentation layer, not just the web one.
"""

import getpass
import service
import storage
import auth


def login_or_register() -> dict:
    print("=== TaskPilot login ===")
    username = input("Username: ").strip()
    existing = storage.get_user_by_username(username)

    if existing:
        password = getpass.getpass("Password: ")
        user = auth.authenticate_user(username, password)
        if not user:
            print("Incorrect password.")
            raise SystemExit(1)
        return user
    else:
        print(f"No account found for '{username}'.")
        choice = input("Create a new account with this username? (y/n): ").strip().lower()
        if choice != "y":
            raise SystemExit(0)
        password = getpass.getpass("Choose a password: ")
        hashed = auth.hash_password(password)
        return storage.create_user(username, hashed)


def print_menu():
    print("\n=== TaskPilot ===")
    print("1. Add task/habit")
    print("2. List all")
    print("3. Mark complete")
    print("4. Delete")
    print("5. Weekly stats")
    print("6. Quit")


def handle_add(user_id: int):
    name = input("Name: ").strip()
    kind = input("Type ('task' or 'habit', default 'task'): ").strip() or "task"
    if kind not in ("task", "habit"):
        print("Invalid type, defaulting to 'task'.")
        kind = "task"
    task = service.add_task(user_id, name, kind)
    print(f"Added: [{task.id}] {task.name} ({task.kind})")


def handle_list(user_id: int):
    tasks = service.get_all_tasks(user_id)
    if not tasks:
        print("No tasks yet. Add one!")
        return
    for t in tasks:
        status = "✓ done today" if t.is_completed_today() else "pending"
        streak = f", streak: {t.current_streak()}" if t.kind == "habit" else ""
        print(f"[{t.id}] {t.name} ({t.kind}) - {status}{streak}")


def handle_complete(user_id: int):
    handle_list(user_id)
    try:
        task_id = int(input("Task ID to mark complete: "))
    except ValueError:
        print("Please enter a number.")
        return
    task = service.complete_task(user_id, task_id)
    if task:
        print(f"Marked '{task.name}' complete for today.")
    else:
        print("No task with that ID.")


def handle_delete(user_id: int):
    handle_list(user_id)
    try:
        task_id = int(input("Task ID to delete: "))
    except ValueError:
        print("Please enter a number.")
        return
    if service.delete_task(user_id, task_id):
        print("Deleted.")
    else:
        print("No task with that ID.")


def handle_stats(user_id: int):
    rate = service.weekly_completion_rate(user_id)
    print(f"Weekly completion rate: {rate}%")


def run():
    user = login_or_register()
    print(f"\nWelcome, {user['username']}!")

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
            action(user["id"])
        else:
            print("Invalid option, try again.")


if __name__ == "__main__":
    storage.init_db()
    run()
