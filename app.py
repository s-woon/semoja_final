from flask import Flask, redirect, render_template, request, jsonify, url_for, app
from pymongo import MongoClient
import requests

client = MongoClient('mongodb+srv://test:sparta@cluster0.yoehfpg.mongodb.net/?retryWrites=true&w=majority')
db = client.dbsparta

# JWT 토큰을 만들 때 필요한 비밀문자열입니다. 아무거나 입력해도 괜찮습니다.
# 이 문자열은 서버만 알고있기 때문에, 내 서버에서만 토큰을 인코딩(=만들기)/디코딩(=풀기) 할 수 있습니다.
SECRET_KEY = 'SPARTA'

# 토큰에 만료시간을 줘야하기 때문에, datetime 모듈도 사용합니다.
import datetime

# JWT 패키지를 사용합니다. (설치해야할 패키지 이름: PyJWT)
import jwt

# 회원가입 시엔, 비밀번호를 암호화하여 DB에 저장해두는 게 좋습니다.
# 그렇지 않으면, 개발자(=나)가 회원들의 비밀번호를 볼 수 있으니까요.^^;
import hashlib


# Flask
app = Flask(__name__)

# .env
# load_dotenv()
# ID = os.environ.get('DB_ID')
# PW = os.environ.get('DB_PW')

# ========================================================================================
# 로그인 화면
@app.route('/login')
def login():
    msg = request.args.get("msg")
    return render_template('login.html', msg=msg)

# [로그인 API]
# id, pw를 받아서 맞춰보고, 토큰을 만들어 발급합니다.
@app.route('/api/login', methods=['POST'])
def api_login():
    id_receive = request.form['id_give']
    pw_receive = request.form['pw_give']

    # 회원가입 때와 같은 방법으로 pw를 암호화합니다.
    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    # id, 암호화된pw을 가지고 해당 유저를 찾습니다.
    result = db.user.find_one({'id': id_receive, 'pw': pw_hash})

    # 찾으면 JWT 토큰을 만들어 발급합니다.
    if result is not None:
        # JWT 토큰에는, payload와 시크릿키가 필요합니다.
        # 시크릿키가 있어야 토큰을 디코딩(=풀기) 해서 payload 값을 볼 수 있습니다.
        # 아래에선 id와 exp를 담았습니다. 즉, JWT 토큰을 풀면 유저ID 값을 알 수 있습니다.
        # exp에는 만료시간을 넣어줍니다. 만료시간이 지나면, 시크릿키로 토큰을 풀 때 만료되었다고 에러가 납니다.
        payload = {
            'id': id_receive,
            'exp': datetime.datetime.utcnow() + datetime.timedelta(seconds=50000)
        }
        # pycharm에서 사용시
        token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

        # 우분투 서버에서 사용시
        # token = jwt.encode(payload, SECRET_KEY, algorithm='HS256').decode('utf-8')

        # token을 줍니다.
        return jsonify({'result': 'success', 'token': token})
    # 찾지 못하면
    else:
        return jsonify({'result': 'fail', 'msg': '아이디/비밀번호가 일치하지 않습니다.'})

# [유저 정보 확인 API]
# 로그인된 유저만 call 할 수 있는 API입니다.
# 유효한 토큰을 줘야 올바른 결과를 얻어갈 수 있습니다.
# (그렇지 않으면 남의 장바구니라든가, 정보를 누구나 볼 수 있겠죠?)
@app.route('/api/nick', methods=['GET'])
def api_valid():
    token_receive = request.cookies.get('mytoken')

    # try / catch 문?
    # try 아래를 실행했다가, 에러가 있으면 except 구분으로 가란 얘기입니다.

    try:
        # token을 시크릿키로 디코딩합니다.
        # 보실 수 있도록 payload를 print 해두었습니다. 우리가 로그인 시 넣은 그 payload와 같은 것이 나옵니다.
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        print(payload)

        # payload 안에 id가 들어있습니다. 이 id로 유저정보를 찾습니다.
        # 여기에선 그 예로 닉네임을 보내주겠습니다.
        userinfo = db.user.find_one({'id': payload['id']}, {'_id': 0})
        return jsonify({'result': 'success', 'name': userinfo['name']})
    except jwt.ExpiredSignatureError:
        # 위를 실행했는데 만료시간이 지났으면 에러가 납니다.
        return jsonify({'result': 'fail', 'msg': ''})
    except jwt.exceptions.DecodeError:
        return jsonify({'result': 'fail', 'msg': ''})


# ========================================================================================
# 회원가입 화면
@app.route('/signup', methods=["GET"])
def signup():
    return render_template('signup.html')

# [회원가입 API]
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route("/sign_up/save", methods=["POST"])
def api_register():
    id_receive = request.form['id_give']
    pw_receive = request.form['password_give']
    name_receive = request.form['name_give']
    email_receive = request.form['num_give']
    num_receive = request.form['email_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    doc = {
        'id':id_receive,
        'pw': pw_hash,
        'name': name_receive,
        'email': email_receive,
        'num': num_receive
    }

    db.user.insert_one(doc)
    return jsonify({'msg': '회원가입이 완료되었습니다.'})

# 아이디 중복확인
@app.route('/sign_up/check_dup', methods=['POST'])
def check_dup():
    username_receive = request.form['username_give']
    exists = bool(db.user.find_one({"id": username_receive}))
    print(exists)
    return jsonify({'result': 'success', 'exists': exists})

# ========================================================================================
# 세모자 메인 카테고리 화면
@app.route('/')
def home():
    token_receive = request.cookies.get('mytoken')
    try:
        payload = jwt.decode(token_receive, SECRET_KEY, algorithms=['HS256'])
        user_info = db.user.find_one({"id": payload['id']})
        print(user_info)
        return render_template('index.html', nickname=user_info["id"])
    except jwt.ExpiredSignatureError:
        return redirect(url_for("login", msg="로그인 시간이 만료되었습니다."))
    except jwt.exceptions.DecodeError:
        return redirect(url_for("login", msg="로그인 정보가 존재하지 않습니다."))

# MongoDB 데이터 가져오기
@app.route("/certificate", methods=["GET"])
def certificate_get():
    certificate_list = list(db.certificate.find({}, {'_id': False}))
    return jsonify({'certificates': certificate_list})

# 자격증 검색기능
@app.route("/certificate/search", methods=["POST"])
def search_certificate():
    user_input_receive = request.form["input_give"]
    certificate = list(db.certificate.find({}, {'_id': False}))
    search_list = []
    for i in certificate:
        jmNm = i["jmNm"]
        if jmNm == None:
            pass
        elif user_input_receive in jmNm:
            search_list.append(i)
    return jsonify({'result': search_list})


# ========================================================================================
# 세모자 자격증 세부정보
@app.route('/certificateDetails/<id>/<index>/<num>', methods=["GET"])
def certificate_Details(id,index,num):
    certificate = list(db.certificate.find({}, {'_id': False}))
    for i in range(0,len(certificate)):
        if int(certificate[i]['index']) == int(index) and int(certificate[i]['certificateNum']) == int(num):
            certificateNum = certificate[i]["certificateNum"]
            implNm = certificate[i]["implNm"]
            click_index = certificate[i]["index"]
            instiNm = certificate[i]["instiNm"]
            jmNm = certificate[i]["jmNm"]
            mdobligFldNm = certificate[i]["mdobligFldNm"]
            summary = certificate[i]["summary"]
    return render_template("certificateDetails.html",
                           id=id,
                           certificateNum=certificateNum,
                           implNm=implNm,
                           click_index=click_index,
                           instiNm=instiNm,
                           jmNm=jmNm,
                           mdobligFldNm=mdobligFldNm,
                           summary=summary)

# 자격증 세부정보 가져오기
@app.route('/certificateDetails/get_detail', methods=["GET"])
def get_certificate_Details():
    certificate_detail = list(db.certificate.find({}, {'_id': False}))
    # result = certificate_detail.json()
    # print(certificate_detail[1]['implNm'])
    return jsonify({'certificate_detail': certificate_detail})

# index : 01 - 기술사 , 02 - 기능장 , 03 - 기사 , 04 - 기능사

# 자격증 세부정보 > 코멘트 DB 저장
@app.route('/certificateDetails/post_comment', methods=["POST"])
def post_certificate_comment():
    comment_receive = request.form["comment_give"]
    certificateNum_receive = request.form["certificateNum_give"]
    click_index_receive = request.form["click_index_give"]
    name_receive = request.form["nickname_give"]
    print(comment_receive, click_index_receive, certificateNum_receive)
    doc = {
        "certificate_index":click_index_receive,
        "certificate_number":certificateNum_receive,
        "comment":comment_receive,
        "name":name_receive
    }
    db.certificate_comment.insert_one(doc)
    return jsonify({'msg':'코멘트 입력이 완료되었습니다.'})

# 자격증 코멘트 불러오기 - 자격증 index, number에 따라 다른 코멘드 불러올것
@app.route('/certificateDetails/comment_list', methods=["GET"])
def comment_list():
    comment_list = list(db.certificate_comment.find({}, {'_id': False}))
    return jsonify({'comment_list': comment_list})

# db.user.insert_one(doc)
# db.certificate.insert_one(doc)

# 회원정보변경 페이지 이동
@app.route('/member_info')
def member_info():
    return render_template("member_info.html")

# 회원정보 변경
# id값을 어디선가 가져와서 keyword로 받아서 DB에서 조회해서 불러온다. - 단 PW의 값은 받지 않도록 한다.
@app.route('/member_info/<keyword>', methods=["GET"])
def get_member_info(keyword):
    user_member_info = list(db.user.find({'id':keyword}, {'_id': False}))
    id = user_member_info[0]["id"]
    name = user_member_info[0]["name"]
    num = user_member_info[0]["num"]
    email = user_member_info[0]["email"]
    print(name)
    return render_template("member_info.html", id=id, name=name, num=num, email=email)

# 회원정보 수정 저장
# 저장하기 전에, pw를 sha256 방법(=단방향 암호화. 풀어볼 수 없음)으로 암호화해서 저장합니다.
@app.route("/member_info/save", methods=["POST"])
def post_member_info():
    id_receive = request.form['id_give']
    pw_receive = request.form['password_give']
    name_receive = request.form['name_give']
    email_receive = request.form['num_give']
    num_receive = request.form['email_give']

    pw_hash = hashlib.sha256(pw_receive.encode('utf-8')).hexdigest()

    db.user.update_one({'id': id_receive}, {'$set': {'pw': pw_hash}})
    db.user.update_one({'id': id_receive}, {'$set': {'name': name_receive}})
    db.user.update_one({'id': id_receive}, {'$set': {'num': num_receive}})
    db.user.update_one({'id': id_receive}, {'$set': {'email': email_receive}})

    return jsonify({'msg': '회원정보가 수정되었습니다.'})

if __name__ == '__main__':
    app.run('0.0.0.0', port=5000, debug=True)