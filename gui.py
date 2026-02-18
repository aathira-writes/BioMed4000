import tkinter as tk
from tkinter import messagebox
from login import login, create_user
from training import capture_faces

# homescreen

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("MEDICAL INVENTORY SYSTEM")
        self.root.geometry("350x300") #make bigger???
        self.current_user_role = None


        self.show_main_menu()

   
    # main menu
   
    def show_main_menu(self):
        self.clear_window()

        tk.Label(self.root, text="BioMed Access System", font=("Arial", 16)).pack(pady=20)

        tk.Button(self.root, text="Login", width=20, command=self.show_login).pack(pady=10)
        tk.Button(self.root, text="Create New User", width=20, command=self.show_create_user).pack(pady=10)
        tk.Button(self.root, text="Exit", width=20, command=self.root.quit).pack(pady=10)


    # login screen

    def show_login(self):
        self.clear_window()

        tk.Label(self.root, text="Login", font=("Arial", 16)).pack(pady=20)

        tk.Label(self.root, text="Username").pack()
        username_entry = tk.Entry(self.root)
        username_entry.pack()

        tk.Label(self.root, text="Password").pack()
        password_entry = tk.Entry(self.root, show="*")
        password_entry.pack()

        def attempt_login():
            username = username_entry.get()
            password = password_entry.get()

            result = login(username, password)
            if result is None:
                messagebox.showerror("Error", "Invalid username or password.")
                return

            user_id, role = result
            self.current_user_role = role

            if user_id is None:
                messagebox.showerror("Error", "Invalid username or password.")
            else:
                messagebox.showinfo("Success", f"Login successful! User ID: {user_id}")
                # TODO: Add face recognition step here
                self.show_main_menu()

        tk.Button(self.root, text="Login", width=20, command=attempt_login).pack(pady=10)
        tk.Button(self.root, text="Back", width=20, command=self.show_main_menu).pack()


    # create user

    def show_create_user(self):
        self.clear_window()

        tk.Label(self.root, text="Create New User", font=("Arial", 16)).pack(pady=20)

        tk.Label(self.root, text="Username").pack()
        username_entry = tk.Entry(self.root)
        username_entry.pack()

        tk.Label(self.root, text="Password").pack()
        password_entry = tk.Entry(self.root, show="*")
        password_entry.pack()


        def save_user():
            username = username_entry.get()
            password = password_entry.get()

            if not username or not password:
                messagebox.showerror("Error", "All fields are required.")
                return

            # Step 1: Capture face images
            messagebox.showinfo("Face Capture", "The camera will open. Be prepared to show multiple angles of your face in quick succession.")
            capture_faces(username, num_images=50)

            # Step 2: Save user to database
            create_user(username, password)

            messagebox.showinfo("Success", f"User '{username}' created and face data captured.")
            self.show_main_menu()

        tk.Button(self.root, text="Create User", width=20, command=save_user).pack(pady=10)
        tk.Button(self.root, text="Back", width=20, command=self.show_main_menu).pack()


    # this one makes the window dissapear when they pick exit

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()



# gotta make sure it runs

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
    
