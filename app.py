import os
from flask import Flask, request, jsonify, render_template, Response
from flask_sqlalchemy import SQLAlchemy
from flask_admin import Admin  # Flask-Admin
from flask_admin.contrib.sqla import ModelView # DB 모델 뷰

# --- 1. 기본 설정 ---
basedir = os.path.abspath(os.path.dirname(__file__))

app = Flask(__name__)
# DB 파일 경로 설정
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///' + os.path.join(basedir, 'moducare.db')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = 'moducare-super-secret-key' # 관리자 세션용 비밀 키

db = SQLAlchemy(app)

# --- 2. 데이터베이스 모델 정의 ---

# 2-1. 장애학생(사용자) 모델
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    name = db.Column(db.String(100), nullable=False)
    student_id = db.Column(db.String(20), unique=True, nullable=False)
    department = db.Column(db.String(100))
    disability_type = db.Column(db.String(100))
    needs = db.Column(db.Text)
    assistive_device = db.Column(db.String(200))

    def __repr__(self):
        return f'<User {self.name}>'

# 2-2. 예약 정보 모델
class Booking(db.Model):
    id = db.Column(db.Integer, primary_key=True) # 예약 고유 ID
    name = db.Column(db.String(100), nullable=False) # 예약자 성명
    phone = db.Column(db.String(100), nullable=False) # 연락처
    service_type = db.Column(db.String(50)) # 서비스 유형
    start_date = db.Column(db.String(50)) # 희망 시작일
    time_slot = db.Column(db.String(50)) # 희망 시간대
    notes = db.Column(db.Text) # 특이사항

    def __repr__(self):
        return f'<Booking {self.name} - {self.start_date}>'


# --- 3. 관리자 페이지 보안 설정 ---

# 관리자 아이디/비밀번호 (간단 설정)
def check_auth(username, password):
    return username == 'admin' and password == '1234'

# 로그인 팝업창 띄우기
def authenticate():
    return Response(
    '접근이 거부되었습니다. 관리자 로그인이 필요합니다.', 401,
    {'WWW-Authenticate': 'Basic realm="Login Required"'})

# 보안이 적용된 User 관리 뷰
class SecuredUserView(ModelView):
    def is_accessible(self):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return False
        return True

    def inaccessible_callback(self, name, **kwargs):
        return authenticate()

# 보안이 적용된 Booking 관리 뷰
class SecuredBookingView(ModelView):
    def is_accessible(self):
        auth = request.authorization
        if not auth or not check_auth(auth.username, auth.password):
            return False
        return True

    def inaccessible_callback(self, name, **kwargs):
        return authenticate()


# --- 4. 관리자 페이지 적용 ---
# (오류가 났던 template_mode 인자 제거)
admin = Admin(app, name='모두케어 관리자')

# 관리자 페이지에 2개의 관리 메뉴 추가
admin.add_view(SecuredUserView(User, db.session, name="장애학생 관리"))
admin.add_view(SecuredBookingView(Booking, db.session, name="예약 내역 관리"))


# --- 5. API 및 페이지 라우트(경로) 설정 ---

# [GET] / : 메인 HTML 페이지 보여주기
@app.route('/')
def home():
    # templates 폴더 안의 index.html을 찾아서 보여줌
    return render_template('index.html')

# [POST] /booking : 예약 정보 받아서 저장하기 (API)
@app.route('/booking', methods=['POST'])
def create_booking():
    data = request.get_json()
    new_booking = Booking(
        name=data['name'],
        phone=data['phone'],
        service_type=data.get('serviceType', ''),
        start_date=data.get('date', ''),
        time_slot=data.get('time', ''),
        notes=data.get('notes', '')
    )
    db.session.add(new_booking)
    db.session.commit()
    return jsonify({'message': '예약이 성공적으로 데이터베이스에 저장되었습니다.'}), 201

# --- (학생 정보 API) ---

# [POST] /user : 새 학생 등록 (API)
@app.route('/user', methods=['POST'])
def create_user():
    data = request.get_json()
    new_user = User(
        username=data['username'],
        name=data['name'],
        student_id=data['student_id'],
        department=data.get('department', ''),
        disability_type=data.get('disability_type', ''),
        needs=data.get('needs', ''),
        assistive_device=data.get('assistive_device', '')
    )
    db.session.add(new_user)
    db.session.commit()
    return jsonify({'message': f'{new_user.name} 님, 등록이 완료되었습니다.'}), 201

# [GET] /users : 모든 학생 목록 (API)
@app.route('/users', methods=['GET'])
def get_all_users():
    users = User.query.all()
    output = []
    for user in users:
        user_data = {
            'id': user.id,
            'name': user.name,
            'student_id': user.student_id,
            'department': user.department,
            'disability_type': user.disability_type
        }
        output.append(user_data)
    return jsonify({'users': output})

# [GET] /user/<int:id> : 특정 학생 정보 (API)
@app.route('/user/<int:id>', methods=['GET'])
def get_user(id):
    user = User.query.get_or_404(id)
    user_data = {
        'id': user.id,
        'username': user.username,
        'name': user.name,
        'student_id': user.student_id,
        'department': user.department,
        'disability_type': user.disability_type,
        'needs': user.needs,
        'assistive_device': user.assistive_device
    }
    return jsonify({'user': user_data})

# --- 6. 서버 실행 ---
if __name__ == '__main__':
    with app.app_context():
        db.create_all() # DB 파일 및 테이블 자동 생성
    app.run(debug=True, port=5000)