import sqlite3

def check_database_structure():
    """Check the actual structure of the database"""
    conn = sqlite3.connect('customer_supplier.db')
    cursor = conn.cursor()
    
    try:
        # Check sales_invoice table structure
        print("=== SALES_INVOICE TABLE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(sales_invoice)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}, PK: {col[5]}")
        
        print("\n=== PURCHASE_INVOICE TABLE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(purchase_invoice)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}, PK: {col[5]}")
            
        print("\n=== COLLECTION TABLE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(collection)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}, PK: {col[5]}")
            
        print("\n=== PAYMENT TABLE STRUCTURE ===")
        cursor.execute("PRAGMA table_info(payment)")
        columns = cursor.fetchall()
        for col in columns:
            print(f"Column: {col[1]}, Type: {col[2]}, NotNull: {col[3]}, Default: {col[4]}, PK: {col[5]}")
            
    except Exception as e:
        print(f"Error: {e}")
    finally:
        conn.close()

if __name__ == "__main__":
    check_database_structure()
