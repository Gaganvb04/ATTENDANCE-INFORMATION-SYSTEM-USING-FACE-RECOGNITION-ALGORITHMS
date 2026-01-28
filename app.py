from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from flask_mysqldb import MySQL
from werkzeug.security import generate_password_hash, check_password_hash
from werkzeug.utils import secure_filename
import os
import cv2
import numpy as np
import base64
from datetime import datetime, date
import insightface
from insightface.app import FaceAnalysis
import pickle
from functools import wraps

app = Flask(__name__)
app.secret_key = 'your-secret-key-change-this-in-production'

# MySQL Configuration
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = 'Face@123'
app.config['MYSQL_DB'] = 'attendance_system'

# Upload Configuration
UPLOAD_FOLDER = 'static/uploads'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

mysql = MySQL(app)

# Initialize Face Recognition
class FaceRecognitionSystem:
    def __init__(self):
        self.app = FaceAnalysis(providers=['CUDAExecutionProvider', 'CPUExecutionProvider'])
        self.app.prepare(ctx_id=0, det_size=(640, 640))
        
    def extract_embedding(self, image):
        """Extract face embedding from image - returns single face"""
        faces = self.app.get(image)
        if len(faces) == 1:
            return faces[0].embedding, True
        elif len(faces) == 0:
            return None, False  # No face detected
        else:
            return None, False  # Multiple faces detected
    
    def extract_multiple_embeddings(self, image):
        """
        Extract embeddings from all detected faces in the image
        
        Returns:
            list of tuples: [(embedding, bbox, confidence), ...]
            success: boolean
        """
        faces = self.app.get(image)
        
        if len(faces) == 0:
            return [], False
        
        # Extract all face embeddings with their metadata
        face_data = []
        for face in faces:
            face_info = {
                'embedding': face.embedding,
                'bbox': face.bbox,
                'confidence': face.det_score,
                'landmarks': face.kps if hasattr(face, 'kps') else None
            }
            face_data.append(face_info)
        
        return face_data, True
    
    def compare_embeddings(self, emb1, emb2, threshold=0.4):
        """Compare two face embeddings"""
        similarity = np.dot(emb1, emb2) / (np.linalg.norm(emb1) * np.linalg.norm(emb2))
        return similarity > threshold, similarity

# Initialize face recognition system
face_system = FaceRecognitionSystem()

# Helper functions
def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'admin_logged_in' not in session:
            flash('Please login first', 'danger')
            return redirect(url_for('admin_login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    return render_template('index.html')

@app.route('/admin/login', methods=['GET', 'POST'])
def admin_login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        
        cur = mysql.connection.cursor()
        cur.execute("SELECT * FROM admin WHERE username = %s", [username])
        admin = cur.fetchone()
        cur.close()
        
        if admin and check_password_hash(admin[2], password):
            session['admin_logged_in'] = True
            session['admin_id'] = admin[0]
            session['admin_username'] = admin[1]
            flash('Login successful!', 'success')
            return redirect(url_for('admin_dashboard'))
        else:
            flash('Invalid credentials', 'danger')
    
    return render_template('admin_login.html')

@app.route('/admin/dashboard')
@login_required
def admin_dashboard():
    cur = mysql.connection.cursor()
    
    # Get statistics
    cur.execute("SELECT COUNT(*) FROM students")
    total_students = cur.fetchone()[0]
    
    cur.execute("SELECT COUNT(*) FROM faculty")
    total_faculty = cur.fetchone()[0]
    
    # Get today's attendance
    today = date.today()
    cur.execute("""
        SELECT COUNT(DISTINCT student_id) 
        FROM attendance 
        WHERE session_date = %s AND status = 'present'
    """, [today])
    present_today = cur.fetchone()[0]
    
    cur.close()
    
    return render_template('admin_dashboard.html', 
                         total_students=total_students,
                         total_faculty=total_faculty,
                         present_today=present_today)

@app.route('/admin/logout')
def admin_logout():
    session.clear()
    flash('Logged out successfully', 'success')
    return redirect(url_for('admin_login'))

@app.route('/register/student', methods=['GET', 'POST'])
@login_required
def register_student():
    if request.method == 'POST':
        # Get form data
        roll_number = request.form['roll_number']
        name = request.form['name']
        branch = request.form['branch']
        dob = request.form['dob']
        mobile = request.form['mobile']
        email = request.form['email']
        address = request.form['address']
        
        # Get face image from webcam
        face_data = request.form['face_data']
        
        # Decode base64 image
        image_data = base64.b64decode(face_data.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Extract face embedding (single face for registration)
        embedding, success = face_system.extract_embedding(image)
        
        if not success:
            flash('Face not detected or multiple faces detected. Please try again with only one person.', 'danger')
            return redirect(url_for('register_student'))
        
        # Save photo
        photo_filename = f"{roll_number}_{datetime.now().strftime('%Y%m%d%H%M%S')}.jpg"
        photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'students', photo_filename)
        os.makedirs(os.path.dirname(photo_path), exist_ok=True)
        cv2.imwrite(photo_path, image)
        
        # Serialize embedding
        embedding_blob = pickle.dumps(embedding)
        
        # Insert into database
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO students 
                (roll_number, name, branch, date_of_birth, mobile_number, mail_id, address, photo_path, face_embedding)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
            """, (roll_number, name, branch, dob, mobile, email, address, photo_path, embedding_blob))
            mysql.connection.commit()
            flash('Student registered successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    return render_template('register_student.html')

@app.route('/register/faculty', methods=['GET', 'POST'])
@login_required
def register_faculty():
    if request.method == 'POST':
        emp_id = request.form['emp_id']
        name = request.form['name']
        department = request.form['department']
        mobile = request.form['mobile']
        photo_path = None
        
        # Handle photo upload
        if 'photo' in request.files:
            file = request.files['photo']
            if file and allowed_file(file.filename):
                filename = secure_filename(f"{emp_id}_{file.filename}")
                photo_path = os.path.join(app.config['UPLOAD_FOLDER'], 'faculty', filename)
                os.makedirs(os.path.dirname(photo_path), exist_ok=True)
                file.save(photo_path)
        
        cur = mysql.connection.cursor()
        try:
            cur.execute("""
                INSERT INTO faculty (emp_id, name, department, mobile_number, photo_path)
                VALUES (%s, %s, %s, %s, %s)
            """, (emp_id, name, department, mobile, photo_path))
            mysql.connection.commit()
            flash('Faculty registered successfully!', 'success')
            return redirect(url_for('admin_dashboard'))
        except Exception as e:
            mysql.connection.rollback()
            flash(f'Error: {str(e)}', 'danger')
        finally:
            cur.close()
    
    return render_template('register_faculty.html')

@app.route('/attendance/mark', methods=['GET', 'POST'])
@login_required
def mark_attendance():
    if request.method == 'GET':
        # Get faculty list for dropdown
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, name, emp_id FROM faculty")
        faculty_list = cur.fetchall()
        cur.close()
        return render_template('mark_attendance.html', faculty_list=faculty_list)
    
    if request.method == 'POST':
        faculty_id = request.form['faculty_id']
        subject = request.form['subject']
        period = request.form['period']
        face_data = request.form['face_data']
        
        # Decode image
        image_data = base64.b64decode(face_data.split(',')[1])
        nparr = np.frombuffer(image_data, np.uint8)
        image = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
        
        # Extract embeddings for ALL faces in the image
        face_data_list, success = face_system.extract_multiple_embeddings(image)
        
        if not success or len(face_data_list) == 0:
            return jsonify({'success': False, 'message': 'No faces detected in the image'})
        
        # Get all students from database
        cur = mysql.connection.cursor()
        cur.execute("SELECT id, roll_number, name, face_embedding FROM students")
        students = cur.fetchall()
        
        today = date.today()
        recognized_students = []
        unrecognized_count = 0
        already_marked_count = 0
        
        # Process each detected face
        for face_info in face_data_list:
            detected_embedding = face_info['embedding']
            detected_confidence = face_info['confidence']
            
            # Try to match with database
            best_match = None
            max_similarity = 0
            
            for student in students:
                student_id, roll_no, name, emb_blob = student
                stored_embedding = pickle.loads(emb_blob)
                is_match, similarity = face_system.compare_embeddings(
                    detected_embedding, 
                    stored_embedding,
                    threshold=0.4
                )
                
                if is_match and similarity > max_similarity:
                    max_similarity = similarity
                    best_match = (student_id, roll_no, name)
            
            # If match found, mark attendance
            if best_match:
                student_id, roll_no, name = best_match
                
                # Check if already marked
                cur.execute("""
                    SELECT id FROM attendance 
                    WHERE student_id = %s AND session_date = %s AND period_number = %s
                """, (student_id, today, period))
                
                existing = cur.fetchone()
                
                if existing:
                    already_marked_count += 1
                    recognized_students.append({
                        'name': name,
                        'roll_number': roll_no,
                        'status': 'already_marked',
                        'confidence': float(max_similarity)
                    })
                else:
                    # Mark attendance
                    cur.execute("""
                        INSERT INTO attendance 
                        (student_id, faculty_id, subject, session_date, period_number, status, confidence_score)
                        VALUES (%s, %s, %s, %s, %s, 'present', %s)
                    """, (student_id, faculty_id, subject, today, period, float(max_similarity)))
                    
                    mysql.connection.commit()
                    
                    recognized_students.append({
                        'name': name,
                        'roll_number': roll_no,
                        'status': 'marked',
                        'confidence': float(max_similarity)
                    })
            else:
                unrecognized_count += 1
        
        cur.close()
        
        # Prepare response message
        total_faces = len(face_data_list)
        marked_count = len([s for s in recognized_students if s['status'] == 'marked'])
        
        if marked_count > 0:
            message = f"Marked {marked_count} student(s) present. "
            if already_marked_count > 0:
                message += f"{already_marked_count} already marked. "
            if unrecognized_count > 0:
                message += f"{unrecognized_count} face(s) not recognized."
            
            return jsonify({
                'success': True,
                'message': message,
                'details': {
                    'total_faces': total_faces,
                    'marked': marked_count,
                    'already_marked': already_marked_count,
                    'unrecognized': unrecognized_count,
                    'students': recognized_students
                }
            })
        elif already_marked_count > 0:
            return jsonify({
                'success': False,
                'message': f"All {already_marked_count} student(s) already marked present",
                'details': {
                    'total_faces': total_faces,
                    'already_marked': already_marked_count,
                    'students': recognized_students
                }
            })
        else:
            return jsonify({
                'success': False,
                'message': f"Detected {total_faces} face(s) but none recognized",
                'details': {
                    'total_faces': total_faces,
                    'unrecognized': unrecognized_count
                }
            })

@app.route('/attendance/end-session', methods=['POST'])
@login_required
def end_session():
    """
    Mark all students who haven't been marked as absent when session ends
    """
    faculty_id = request.form['faculty_id']
    subject = request.form['subject']
    period = request.form['period']
    today = date.today()
    
    cur = mysql.connection.cursor()
    
    try:
        # Mark absent for all students who don't have attendance record
        cur.execute("""
            INSERT INTO attendance (student_id, faculty_id, subject, session_date, period_number, status)
            SELECT s.id, %s, %s, %s, %s, 'absent'
            FROM students s
            WHERE NOT EXISTS (
                SELECT 1 FROM attendance a 
                WHERE a.student_id = s.id 
                AND a.session_date = %s 
                AND a.period_number = %s
            )
        """, (faculty_id, subject, today, period, today, period))
        
        absent_count = cur.rowcount
        mysql.connection.commit()
        
        return jsonify({
            'success': True,
            'message': f'Session ended. Marked {absent_count} student(s) as absent',
            'absent_count': absent_count
        })
        
    except Exception as e:
        mysql.connection.rollback()
        return jsonify({
            'success': False,
            'message': f'Error ending session: {str(e)}'
        })
    finally:
        cur.close()

@app.route('/attendance/view')
@login_required
def view_attendance():
    date_filter = request.args.get('date', date.today())
    
    cur = mysql.connection.cursor()
    cur.execute("""
        SELECT s.roll_number, s.name, a.subject, a.period_number, 
               a.status, a.marked_at, a.confidence_score
        FROM attendance a
        JOIN students s ON a.student_id = s.id
        WHERE a.session_date = %s
        ORDER BY a.period_number, s.roll_number
    """, [date_filter])
    
    attendance_records = cur.fetchall()
    cur.close()
    
    return render_template('view_attendance.html', records=attendance_records, date=date_filter)

@app.route('/students/list')
@login_required
def list_students():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, roll_number, name, branch, mobile_number, mail_id FROM students")
    students = cur.fetchall()
    cur.close()
    
    return render_template('list_students.html', students=students)

@app.route('/faculty/list')
@login_required
def list_faculty():
    cur = mysql.connection.cursor()
    cur.execute("SELECT id, emp_id, name, department, mobile_number FROM faculty")
    faculty = cur.fetchall()
    cur.close()
    
    return render_template('list_faculty.html', faculty=faculty)

@app.route('/reports/student/<int:student_id>')
@login_required
def student_report(student_id):
    cur = mysql.connection.cursor()
    
    # Get student info
    cur.execute("SELECT roll_number, name, branch FROM students WHERE id = %s", [student_id])
    student = cur.fetchone()
    
    # Get attendance records
    cur.execute("""
        SELECT session_date, subject, period_number, status
        FROM attendance
        WHERE student_id = %s
        ORDER BY session_date DESC, period_number
    """, [student_id])
    records = cur.fetchall()
    
    # Calculate percentage
    cur.execute("""
        SELECT 
            COUNT(*) as total,
            SUM(CASE WHEN status = 'present' THEN 1 ELSE 0 END) as present
        FROM attendance
        WHERE student_id = %s
    """, [student_id])
    stats = cur.fetchone()
    
    cur.close()
    
    percentage = (stats[1] / stats[0] * 100) if stats[0] > 0 else 0
    
    return render_template('student_report.html', 
                         student=student, 
                         records=records,
                         total=stats[0],
                         present=stats[1],
                         percentage=percentage)

if __name__ == '__main__':
    # Create upload directories
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'students'), exist_ok=True)
    os.makedirs(os.path.join(UPLOAD_FOLDER, 'faculty'), exist_ok=True)
    
    app.run(debug=True, host='0.0.0.0', port=5000)