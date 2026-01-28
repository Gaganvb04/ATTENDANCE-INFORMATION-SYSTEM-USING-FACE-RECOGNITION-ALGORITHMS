import sys
import getpass
from werkzeug.security import generate_password_hash
import MySQLdb

def create_admin():
    """Create or update admin user"""
    
    print("=" * 50)
    print("   Attendance System - Admin Setup")
    print("=" * 50)
    print()
    
    # Get database credentials
    print("Enter MySQL Database Credentials:")
    db_host = input("Host [localhost]: ").strip() or 'localhost'
    db_user = input("Username [root]: ").strip() or 'root'
    db_password = getpass.getpass("Password: ")
    db_name = input("Database [attendance_system]: ").strip() or 'attendance_system'
    
    try:
        # Connect to database
        print("\nConnecting to database...")
        connection = MySQLdb.connect(
            host=db_host,
            user=db_user,
            passwd=db_password,
            db=db_name
        )
        cursor = connection.cursor()
        print("✓ Connected successfully!")
        
        # Get admin credentials
        print("\n" + "=" * 50)
        print("Enter Admin Account Details:")
        print("=" * 50)
        
        admin_username = input("Admin Username: ").strip()
        while not admin_username:
            print("Username cannot be empty!")
            admin_username = input("Admin Username: ").strip()
        
        admin_password = getpass.getpass("Admin Password: ")
        while len(admin_password) < 6:
            print("Password must be at least 6 characters!")
            admin_password = getpass.getpass("Admin Password: ")
        
        confirm_password = getpass.getpass("Confirm Password: ")
        while admin_password != confirm_password:
            print("Passwords don't match!")
            admin_password = getpass.getpass("Admin Password: ")
            confirm_password = getpass.getpass("Confirm Password: ")
        
        # Hash password
        hashed_password = generate_password_hash(admin_password)
        
        # Check if admin exists
        cursor.execute("SELECT id FROM admin WHERE username = %s", [admin_username])
        existing_admin = cursor.fetchone()
        
        if existing_admin:
            # Update existing admin
            print(f"\nAdmin '{admin_username}' already exists. Updating password...")
            cursor.execute(
                "UPDATE admin SET password = %s WHERE username = %s",
                [hashed_password, admin_username]
            )
            connection.commit()
            print(f"✓ Password updated for admin '{admin_username}'")
        else:
            # Create new admin
            print(f"\nCreating new admin '{admin_username}'...")
            cursor.execute(
                "INSERT INTO admin (username, password) VALUES (%s, %s)",
                [admin_username, hashed_password]
            )
            connection.commit()
            print(f"✓ Admin '{admin_username}' created successfully!")
        
        # Display summary
        print("\n" + "=" * 50)
        print("   Setup Complete!")
        print("=" * 50)
        print(f"\nAdmin Username: {admin_username}")
        print(f"Admin Password: {'*' * len(admin_password)}")
        print(f"\nYou can now login at: http://localhost:5000/admin/login")
        print("\n⚠️  Keep your credentials safe!")
        print("=" * 50)
        
        # Close connection
        cursor.close()
        connection.close()
        
        return True
        
    except MySQLdb.Error as e:
        print(f"\n❌ Database Error: {e}")
        print("\nPlease ensure:")
        print("1. MySQL service is running")
        print("2. Database credentials are correct")
        print("3. Database 'attendance_system' exists")
        print("4. Run: mysql -u root -p < database_schema.sql")
        return False
    
    except KeyboardInterrupt:
        print("\n\n⚠️  Setup cancelled by user")
        return False
    
    except Exception as e:
        print(f"\n❌ Unexpected Error: {e}")
        return False

def main():
    """Main function"""
    print("\n")
    success = create_admin()
    
    if success:
        sys.exit(0)
    else:
        sys.exit(1)

if __name__ == "__main__":
    main()