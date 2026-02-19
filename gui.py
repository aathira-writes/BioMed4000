import tkinter as tk
from tkinter import messagebox
from login import login, create_user
from training import capture_faces
from faces import recognize_user
from identity import verify_identity
from tkinter import messagebox
from train_model import train_model
import calendar 
import datetime 

# homescreen

class App:
    def __init__(self, root):
        self.root = root
        self.root.title("MEDICAL INVENTORY SYSTEM")
        self.root.geometry("700x600") #make bigger???
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

            messagebox.showinfo("Face Verification", "Camera will open. Please look at the camera.")

            detected_id = recognize_user()

            success, msg = verify_identity(user_id, detected_id)

            success, msg = verify_identity(user_id, detected_id)

            if success:
                messagebox.showinfo("Access Granted", msg)
                self.show_home_page(user_id)   #  NEW REDIRECT
            else:
                messagebox.showerror("Access Denied", msg)
                self.show_main_menu()


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

            user_id = create_user(username, password)
            if user_id is None:
                messagebox.showerror("Error", "Username already exists.")
                return

            messagebox.showinfo("Face Capture", "Camera will open now.")
            capture_faces(user_id, num_images=50)

            train_model()

            messagebox.showinfo("Success", f"User '{username}' created.")
            self.show_main_menu()

        tk.Button(self.root, text="Create User", command=save_user).pack(pady=10)
        tk.Button(self.root, text="Back", command=self.show_main_menu).pack()


    def show_home_page(self, user_id):
        self.clear_window()

        # Store current user ID
        self.current_user_id = user_id

        # --- TOP BAR ---
        top_frame = tk.Frame(self.root)
        top_frame.pack(fill="x", pady=10)

        tk.Label(
            top_frame,
            text=f"Logged in as: User {user_id}",
            font=("Arial", 12, "bold")
        ).pack(side="left", padx=10)

        tk.Button(
            top_frame,
            text="Logout",
            command=self.show_login_screen,
            width=10
        ).pack(side="right", padx=10)

        # --- CALENDAR ---
        today = datetime.date.today()
        year = today.year
        month = today.month

        cal = calendar.monthcalendar(year, month)

        cal_frame = tk.Frame(self.root)
        cal_frame.pack(pady=20)

        # Weekday headers
        days = ["Mon", "Tue", "Wed", "Thu", "Fri", "Sat", "Sun"]
        for i, day in enumerate(days):
            tk.Label(
                cal_frame,
                text=day,
                font=("Arial", 12, "bold"),
                borderwidth=1,
                relief="solid",
                width=10,
                height=2
            ).grid(row=0, column=i)

        # Calendar days
        for row_idx, week in enumerate(cal, start=1):
            for col_idx, day in enumerate(week):
                text = "" if day == 0 else str(day)
                tk.Label(
                    cal_frame,
                    text=text,
                    font=("Arial", 12),
                    borderwidth=1,
                    relief="solid",
                    width=10,
                    height=4
                ).grid(row=row_idx, column=col_idx)


    # this one makes the window dissapear when they pick exit

    def clear_window(self):
        for widget in self.root.winfo_children():
            widget.destroy()



# gotta make sure it runs

if __name__ == "__main__":
    root = tk.Tk()
    app = App(root)
    root.mainloop()
    
