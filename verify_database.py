"""
Database Verification and Fix Script
This script checks if the database is properly set up and fixes common issues
"""

import sys
import getpass
import MySQLdb
from werkzeug.security import generate_password_hash

def connect_to_mysql(host, user, password, database=None):
    """Connect to MySQL"""
    try:
        if database:
            conn = MySQLdb.connect(
                host=host,
                user=user,
                passwd=password,
                db=database
            )
        else:
            conn = MySQLdb.connect(
                host=host,
                user=user,
                passwd=password
            )
        return conn
    except Exception as e:
        print(f"❌ Connection failed: {e}")
        return None

def check_database_exists(cursor, db_name):
    """Check if database exists"""
    cursor.execute("SHOW DATABASES LIKE %s", [db_name])
    return cursor.fetchone() is not None

def check_table_exists(cursor, table_name):
    """Check if table exists"""
    cursor.execute("SHOW TABLES LIKE %s", [table_name])
    return cursor.fetchone() is not None

def check_column_exists(cursor, table_name, column_name):
    """Check if column exists in table"""
    cursor.execute(f"SHOW COLUMNS FROM {table_name} LIKE %s", [column_name])
    return cursor.fetchone() is not None

def verify_database():
    """Main verification function"""
    
    print("=" * 60)
    print("  Database Verification and Fix Tool")
    print("=" * 60)
    print()
    
    # Get MySQL credentials
    print("Enter MySQL credentials:")
    host = input("Host [localhost]: ").strip() or 'localhost'
    user = input("Username [root]: ").strip() or 'root'
    password = getpass.getpass("Password: ")
    db_name = 'attendance_system'
    
    # Connect to MySQL
    print("\n1. Connecting to MySQL...")
    conn = connect_to_mysql(host, user, password)
    if not conn:
        return False
    
    cursor = conn.cursor()
    print("✓ Connected to MySQL")
    
    # Check if database exists
    print("\n2. Checking database...")
    if not check_database_exists(cursor, db_name):
        print(f"❌ Database '{db_name}' does not exist")
        print("\nCreating database...")
        cursor.execute(f"CREATE DATABASE {db_name}")
        print(f"✓ Database '{db_name}' created")
    else:
        print(f"✓ Database '{db_name}' exists")
    
    # Connect to the database
    conn.close()
    conn = connect_to_mysql(host, user, password, db_name)
    cursor = conn.cursor()
    
    # Required tables
    required_tables = {
        'admin': ['id', 'username', 'password', 'created_at'],
        'students': ['id', 'roll_number', 'name', 'branch', 'date_of_birth', 
                    'mobile_number', 'mail_id', 'address', 'photo_path', 
                    'face_embedding', 'created_at'],
        'faculty': ['id', 'emp_id', 'name', 'department', 'mobile_number', 
                   'photo_path', 'created_at'],
        'attendance': ['id', 'student_id', 'faculty_id', 'subject', 'session_date', 
                      'period_number', 'status', 'confidence_score', 'marked_at']
    }
    
    # Check each table
    print("\n3. Checking tables and columns...")
    all_good = True
    
    for table_name, columns in required_tables.items():
        print(f"\n   Table: {table_name}")
        
        if not check_table_exists(cursor, table_name):
            print(f"   ❌ Table '{table_name}' missing")
            all_good = False
            continue
        
        print(f"   ✓ Table exists")
        
        # Check columns
        missing_columns = []
        for column in columns:
            if not check_column_exists(cursor, table_name, column):
                missing_columns.append(column)
        
        if missing_columns:
            print(f"   ❌ Missing columns: {', '.join(missing_columns)}")
            all_good = False
        else:
            print(f"   ✓ All columns present")
    
    # If not all good, offer to recreate
    if not all_good:
        print("\n" + "=" * 60)
        print("⚠️  Database has issues!")
        print("=" * 60)
        print("\nWould you like to:")
        print("1. Drop and recreate database (WILL DELETE ALL DATA)")
        print("2. Exit and fix manually")
        
        choice = input("\nEnter choice (1/2): ").strip()
        
        if choice == '1':
            print("\n⚠️  WARNING: This will delete ALL existing data!")
            confirm = input("Type 'YES' to confirm: ").strip()
            
            if confirm == 'YES':
                print("\nRecreating database...")
                
                # Read and execute schema file
                try:
                    with open('database_schema.sql', 'r') as f:
                        sql_script = f.read()
                    
                    # Split by statements and execute
                    statements = sql_script.split(';')
                    
                    for statement in statements:
                        statement = statement.strip()
                        if statement and not statement.startswith('--'):
                            try:
                                cursor.execute(statement)
                            except Exception as e:
                                if 'Unknown database' not in str(e):
                                    print(f"   Warning: {e}")
                    
                    conn.commit()
                    print("✓ Database recreated successfully")
                    
                    # Verify again
                    print("\nVerifying...")
                    conn.close()
                    return verify_database()
                    
                except FileNotFoundError:
                    print("❌ database_schema.sql not found")
                    print("\nPlease run this command manually:")
                    print(f"mysql -u {user} -p < database_schema.sql")
                    return False
                except Exception as e:
                    print(f"❌ Error: {e}")
                    return False
            else:
                print("Operation cancelled")
                return False
        else:
            print("\nPlease fix the database manually and try again")
            print("\nRun this command:")
            print(f"mysql -u {user} -p < database_schema.sql")
            return False
    
    # Check admin account
    print("\n4. Checking admin account...")
    cursor.execute("SELECT COUNT(*) FROM admin")
    admin_count = cursor.fetchone()[0]
    
    if admin_count == 0:
        print("❌ No admin account found")
        print("\nCreating default admin account...")
        
        admin_username = input("Admin username [admin]: ").strip() or 'admin'
        admin_password = getpass.getpass("Admin password: ")
        
        hashed_password = generate_password_hash(admin_password)
        cursor.execute(
            "INSERT INTO admin (username, password) VALUES (%s, %s)",
            [admin_username, hashed_password]
        )
        conn.commit()
        print(f"✓ Admin account '{admin_username}' created")
    else:
        print(f"✓ Admin account exists ({admin_count} account(s))")
    
    # Final summary
    print("\n" + "=" * 60)
    print("  Verification Complete!")
    print("=" * 60)
    print("\n✅ Database is properly configured")
    print("\nYou can now run the application:")
    print("  python app.py")
    print("\nAccess at: http://localhost:5000")
    
    cursor.close()
    conn.close()
    
    return True

def show_current_structure():
    """Show current database structure"""
    
    print("\n" + "=" * 60)
    print("  Current Database Structure")
    print("=" * 60)
    
    host = input("\nHost [localhost]: ").strip() or 'localhost'
    user = input("Username [root]: ").strip() or 'root'
    password = getpass.getpass("Password: ")
    
    try:
        conn = MySQLdb.connect(
            host=host,
            user=user,
            passwd=password,
            db='attendance_system'
        )
        cursor = conn.cursor()
        
        cursor.execute("SHOW TABLES")
        tables = cursor.fetchall()
        
        print("\nTables:")
        for table in tables:
            print(f"  - {table[0]}")
            cursor.execute(f"DESCRIBE {table[0]}")
            columns = cursor.fetchall()
            for col in columns:
                print(f"    └─ {col[0]} ({col[1]})")
        
        cursor.close()
        conn.close()
        
    except MySQLdb.Error as e:
        print(f"❌ Error: {e}")

if __name__ == "__main__":
    try:
        print("\nOptions:")
        print("1. Verify and fix database")
        print("2. Show current structure")
        
        choice = input("\nEnter choice (1/2): ").strip()
        
        if choice == '2':
            show_current_structure()
        else:
            success = verify_database()
            sys.exit(0 if success else 1)
            
    except KeyboardInterrupt:
        print("\n\n⚠️  Operation cancelled")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Error: {e}")
        sys.exit(1)