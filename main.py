from login import login, create_user
from faces import recognize_user
from conflict import log_conflict
from medication import dispense_medication

def main():
    while True:
        print("\n=== MAIN MENU ===")
        print("1. Login")
        print("2. Create New User")
        print("3. Exit")

        choice = input("Choose an option: ")

        if choice == "1":
            handle_login()
        elif choice == "2":
            handle_create_user()
        elif choice == "3":
            print("Goodbye.")
            break
        else:
            print("Invalid choice.")

def handle_login():
    print("\n=== LOGIN ===")
    while True:
        username = input("Username: ")
        password = input("Password: ")

        user_id = login(username, password)
        if user_id is not None:
            print(f"Login successful. User ID: {user_id}")
            break
        else:
            print("Try again.\n")


def handle_create_user():
    print("\n=== CREATE NEW USER ===")
    username = input("New username: ")
    password = input("New password: ")

    create_user(username, password)

if __name__ == "__main__":
    main()


