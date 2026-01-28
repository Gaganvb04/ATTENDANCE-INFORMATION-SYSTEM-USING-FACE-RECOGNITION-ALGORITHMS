DROP DATABASE IF EXISTS attendance_system;
CREATE DATABASE attendance_system;
USE attendance_system;

-- =============================================
-- Admin Table
-- =============================================
CREATE TABLE admin (
    id INT PRIMARY KEY AUTO_INCREMENT,
    username VARCHAR(50) UNIQUE NOT NULL,
    password VARCHAR(255) NOT NULL,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- Students Table
-- =============================================
CREATE TABLE students (
    id INT PRIMARY KEY AUTO_INCREMENT,
    roll_number VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    branch VARCHAR(50),
    date_of_birth DATE,
    mobile_number VARCHAR(15),
    mail_id VARCHAR(100),
    address TEXT,
    photo_path VARCHAR(255),
    face_embedding LONGBLOB,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_roll_number (roll_number)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- Faculty Table
-- =============================================
CREATE TABLE faculty (
    id INT PRIMARY KEY AUTO_INCREMENT,
    emp_id VARCHAR(20) UNIQUE NOT NULL,
    name VARCHAR(100) NOT NULL,
    department VARCHAR(50),
    mobile_number VARCHAR(15),
    photo_path VARCHAR(255),
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_emp_id (emp_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- Attendance Table
-- =============================================
CREATE TABLE attendance (
    id INT PRIMARY KEY AUTO_INCREMENT,
    student_id INT NOT NULL,
    faculty_id INT NOT NULL,
    subject VARCHAR(100) NOT NULL,
    session_date DATE NOT NULL,
    period_number INT NOT NULL,
    status ENUM('present', 'absent') DEFAULT 'present',
    confidence_score FLOAT,
    marked_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
    UNIQUE KEY unique_attendance (student_id, session_date, period_number),
    INDEX idx_date (session_date),
    INDEX idx_student (student_id),
    INDEX idx_faculty (faculty_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- Sessions Table
-- =============================================
CREATE TABLE sessions (
    id INT PRIMARY KEY AUTO_INCREMENT,
    faculty_id INT NOT NULL,
    subject VARCHAR(100) NOT NULL,
    session_date DATE NOT NULL,
    period_number INT NOT NULL,
    start_time TIME,
    end_time TIME,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE,
    INDEX idx_session_date (session_date)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- Attendance Log Table (for audit trail)
-- =============================================
CREATE TABLE attendance_log (
    id INT PRIMARY KEY AUTO_INCREMENT,
    attendance_id INT,
    old_status ENUM('present', 'absent'),
    new_status ENUM('present', 'absent'),
    changed_by VARCHAR(50),
    changed_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    INDEX idx_attendance (attendance_id)
) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4;

-- =============================================
-- Insert Default Admin
-- =============================================
-- Password: admin123 (hashed with Werkzeug)
INSERT INTO admin (username, password) VALUES 
('admin', 'scrypt:32768:8:1$xaWvFqRj7KJLrX5z$8c6976e5b5410415bde908bd4dee15dfb167a9c873fc4bb8a81f6f2ab448a918');

-- =============================================
-- Sample Faculty Data (Optional - for testing)
-- =============================================
INSERT INTO faculty (emp_id, name, department, mobile_number) VALUES
('FAC001', 'Dr. Rajesh Kumar', 'Computer Science', '9876543210'),
('FAC002', 'Prof. Priya Sharma', 'Electronics', '9876543211'),
('FAC003', 'Dr. Amit Patel', 'Information Technology', '9876543212');

-- =============================================
-- Views for Reports
-- =============================================

-- View: Attendance Summary by Student
CREATE VIEW attendance_summary AS
SELECT 
    s.id as student_id,
    s.roll_number,
    s.name,
    s.branch,
    COUNT(DISTINCT CASE WHEN a.status = 'present' THEN a.session_date END) as classes_attended,
    COUNT(DISTINCT a.session_date) as total_classes,
    ROUND(
        (COUNT(DISTINCT CASE WHEN a.status = 'present' THEN a.session_date END) * 100.0 / 
        NULLIF(COUNT(DISTINCT a.session_date), 0)), 
        2
    ) as attendance_percentage
FROM students s
LEFT JOIN attendance a ON s.id = a.student_id
GROUP BY s.id, s.roll_number, s.name, s.branch;

-- View: Daily Attendance Summary
CREATE VIEW daily_attendance AS
SELECT 
    a.session_date,
    a.subject,
    a.period_number,
    f.name as faculty_name,
    COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present_count,
    COUNT(CASE WHEN a.status = 'absent' THEN 1 END) as absent_count,
    COUNT(*) as total_students
FROM attendance a
JOIN faculty f ON a.faculty_id = f.id
GROUP BY a.session_date, a.subject, a.period_number, f.name
ORDER BY a.session_date DESC, a.period_number;

-- =============================================
-- Stored Procedures
-- =============================================

DELIMITER //

-- Procedure: Mark all absent students for a session
CREATE PROCEDURE mark_absent_students(
    IN p_session_date DATE,
    IN p_period_number INT,
    IN p_faculty_id INT,
    IN p_subject VARCHAR(100)
)
BEGIN
    INSERT INTO attendance (student_id, faculty_id, subject, session_date, period_number, status)
    SELECT 
        s.id, 
        p_faculty_id, 
        p_subject, 
        p_session_date, 
        p_period_number, 
        'absent'
    FROM students s
    WHERE NOT EXISTS (
        SELECT 1 
        FROM attendance a 
        WHERE a.student_id = s.id 
        AND a.session_date = p_session_date 
        AND a.period_number = p_period_number
    );
END //

-- Procedure: Get student attendance percentage
CREATE PROCEDURE get_student_attendance(
    IN p_student_id INT
)
BEGIN
    SELECT 
        s.roll_number,
        s.name,
        s.branch,
        COUNT(CASE WHEN a.status = 'present' THEN 1 END) as present,
        COUNT(*) as total,
        ROUND((COUNT(CASE WHEN a.status = 'present' THEN 1 END) * 100.0 / COUNT(*)), 2) as percentage
    FROM students s
    LEFT JOIN attendance a ON s.id = a.student_id
    WHERE s.id = p_student_id
    GROUP BY s.id, s.roll_number, s.name, s.branch;
END //

DELIMITER ;

-- =============================================
-- Triggers
-- =============================================

DELIMITER //

-- Trigger: Log attendance updates
CREATE TRIGGER log_attendance_update
AFTER UPDATE ON attendance
FOR EACH ROW
BEGIN
    IF OLD.status != NEW.status THEN
        INSERT INTO attendance_log (attendance_id, old_status, new_status, changed_by)
        VALUES (NEW.id, OLD.status, NEW.status, USER());
    END IF;
END //

DELIMITER ;

-- =============================================
-- Verify Tables Created
-- =============================================
SELECT 'Database setup complete!' as status;
SHOW TABLES;

-- =============================================
-- Display Column Information
-- =============================================
SELECT 'Admin table structure:' as info;
DESCRIBE admin;

SELECT 'Students table structure:' as info;
DESCRIBE students;

SELECT 'Faculty table structure:' as info;
DESCRIBE faculty;

SELECT 'Attendance table structure:' as info;
DESCRIBE attendance;