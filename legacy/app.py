"""Simple interactive menu: python app.py"""
import datetime as dt
import db

def main():
    con = db.connect("expenses.db")
    if con.execute("SELECT COUNT(*) FROM category").fetchone()[0] == 0:
        db.seed(con, n=150)
    while True:
        print("\n1 Add  2 Update  3 Delete  4 Search  5 Monthly summary  6 Over budget  7 Pending sync  0 Exit")
        ch = input("> ").strip()
        try:
            if ch == "1":
                db.add_expense(con, float(input("Amount: ")), input(f"Category {db.CATEGORIES}: "),
                               input("Date (YYYY-MM-DD, blank=today): ") or dt.date.today().isoformat(),
                               input("Note: "))
                print("Saved.")
            elif ch == "2":
                db.update_expense(con, int(input("Expense id: ")), amount=float(input("New amount: ")))
                print("Updated.")
            elif ch == "3":
                db.delete_expense(con, int(input("Expense id: "))); print("Deleted.")
            elif ch == "4":
                for r in db.search(con, input("Text: "), input("Category (blank=any): ") or None)[:20]:
                    print(dict(r))
            elif ch == "5":
                for r in db.monthly_totals(con, input("Month YYYY-MM: ")): print(dict(r))
            elif ch == "6":
                for r in db.over_budget(con, input("Month YYYY-MM: ")): print(dict(r))
            elif ch == "7":
                print(len(db.pending_sync(con)), "entries waiting to sync")
            elif ch == "0":
                break
        except Exception as e:
            print("Error:", e)

if __name__ == "__main__":
    main()
