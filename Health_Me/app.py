from flask import Flask, render_template, request, jsonify, redirect, make_response, session
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from io import BytesIO
import matplotlib
import matplotlib.pyplot as plt
import datetime

# バックエンドを設定
matplotlib.use('Agg')

# Flaskアプリケーションの設定
app = Flask(__name__)
app.secret_key = 'your_secret_key'  # セッション用の秘密鍵を設定

# SQLiteデータベースのURIを設定
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///user_activity.db'
db = SQLAlchemy(app)
migrate = Migrate(app, db)

# Userデータモデルの更新
class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True, nullable=False)
    password = db.Column(db.String(120), nullable=False)
    height = db.Column(db.Float)  # 身長
    weight = db.Column(db.Float)  # 体重
    age = db.Column(db.Integer)  # 年齢
    gender = db.Column(db.String(10))  # 性別
    health_goal = db.Column(db.String(100))  # 健康目標
    date = db.Column(db.DateTime)  # 記録日
    steps = db.Column(db.Integer)  # 歩数
    calorie_intake = db.Column(db.Integer)  # カロリー摂取量
    dashboard_image = db.Column(db.LargeBinary)  # ダッシュボード画像
    bmi = db.Column(db.Float)  # BMI

    def calculate_bmi(self):
        latest_weight_data = UserWeight.query.filter_by(user_id=self.id).order_by(UserWeight.date.desc()).first()

        if latest_weight_data and latest_weight_data.weight:
            height_meters = self.height / 100
            return latest_weight_data.weight / (height_meters ** 2)
        else:
            return None



# 初期BMIを計算する関数
def calculate_initial_bmi(height, weight):
    height_meters = height / 100
    return weight / (height_meters ** 2)

# ユーザーアクティビティデータモデル
class UserActivity(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    steps = db.Column(db.Integer)
    calorie_intake = db.Column(db.Integer)

# ユーザー体重データモデル
class UserWeight(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)
    date = db.Column(db.DateTime, nullable=False)
    weight = db.Column(db.Float, nullable=False)


# ランディングページ: ログインと登録の選択
@app.route('/', methods=['GET'])
def landing_page():
    return render_template('landing_page.html')

# ユーザー登録フォームを更新
@app.route('/register-form')
def register_form():
    return render_template('register.html')

# ユーザー登録処理を更新
@app.route('/register', methods=['POST'])
def register():
    data = request.form
    username = data.get("username")
    password = data.get("password")
    height = float(data.get("height"))
    weight = float(data.get("weight"))
    age = int(data.get("age"))
    gender = data.get("gender")
    health_goal = data.get("health_goal")

    # ユーザー名がすでに存在するか確認
    existing_user = User.query.filter_by(username=username).first()

    if existing_user:
        # 既存のユーザー名が存在する場合、ユーザーに選択肢を提供
        return render_template('registration_conflict.html', existing_user=existing_user)

    # 新しいユーザー情報をデータベースに保存
    user = User(
        username=username,
        password=password,
        height=height,
        weight=weight,
        age=age,
        gender=gender,
        health_goal=health_goal,
        date=datetime.datetime.now().date()  # 現在の日付を保存
    )
    db.session.add(user)
    db.session.commit()

    # BMIと体重の初期データを保存
    initial_bmi = calculate_initial_bmi(height, weight)
    initial_weight_data = UserActivity(user_id=user.id, date=user.date, steps=0, calorie_intake=0)
    db.session.add(initial_weight_data)
    db.session.commit()

    # 新しいユーザーが登録されたことをセッションに記録
    session['new_user_registered'] = True

    # ダッシュボードにリダイレクト
    return redirect('/dashboard')

# 初期BMIを計算する関数
def calculate_initial_bmi(height, weight):
    height_meters = height / 100
    return weight / (height_meters ** 2)

# ホームページを表示
@app.route('/')
def home():
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()

        if user:
            dates = []  # Initialize dates here

            # BMIデータを取得
            bmi_data, dates = get_user_bmi_data(user.id)

            # 体重データを取得
            weight_data, dates_weight = get_user_weight_data(user.id)
            # 体重チャートを生成して保存
            generate_and_save_weight_chart(user, weight_data, dates_weight)

            # ユーザーの健康データをデータベースから取得
            health_data = get_user_activity_data(user.id)

            # パーソナライズされた挨拶を表示
            greeting = f"お帰りなさい、{user.username}さん！"

            # 更新された情報を含むホームページを描画
            return render_template('home.html', user=user, greeting=greeting)

    return redirect('/login-form')

# ダッシュボードのテンプレートを変更する
@app.route('/dashboard', methods=['GET', 'POST'])
def dashboard():
    # もし新しいユーザーが登録された場合はダッシュボードにリダイレクト
    if 'new_user_registered' in session and session['new_user_registered']:
        session.pop('new_user_registered', None)  # セッションから削除
        return redirect('/dashboard')
    
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()

        if user:
            dates = []  # Initialize dates here

            # BMIデータを取得
            bmi_data, dates = get_user_bmi_data(user.id)

            # 体重データを取得
            weight_data, dates_weight = get_user_weight_data(user.id)
            # 体重チャートを生成して保存
            generate_and_save_weight_chart(user, weight_data, dates_weight)

            # ユーザーの健康データをデータベースから取得
            health_data = get_user_activity_data(user.id)

            # Calculate and update BMI (ensure the user's BMI is up-to-date)
            user.bmi = user.calculate_bmi()
            db.session.commit()

            # ダッシュボードにデータを表示する
            return render_template('dashboard.html', data_list=health_data, activity_data=health_data, user=user)

    return redirect('/login-form')



# ログインフォームを表示
@app.route('/login-form', methods=['GET'])
def login_form():
    return render_template('login.html')

# ログイン処理
@app.route('/login', methods=['POST'])
def login():
    data = request.form
    username = data.get("username")
    password = data.get("password")
    user = User.query.filter_by(username=username, password=password).first()
    if user:
        session['username'] = username
        return redirect('/dashboard')  # ログイン成功時にダッシュボードにリダイレクト
    else:
        return jsonify({"message": "Invalid username or password"})

# ログアウト処理
@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect('/')

@app.route('/profile')
def profile():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        return render_template('profile.html', user=user)
    return redirect('/login-form')

# 新しいヘルスデータ取得関数
def get_user_activity_data(user_id):
    # Retrieve user activity data from the database
    user_activity_data = UserActivity.query.filter_by(user_id=user_id).all()
    return user_activity_data

# BMIデータ取得の修正
def get_user_bmi_data(user_id):
    # 特定のユーザーのBMIデータと日付リストをデータベースから取得
    bmi_data = []
    dates = []
    user_activities = UserActivity.query.filter_by(user_id=user_id).all()
    for activity in user_activities:
        if (user := db.session.query(User).get(activity.user_id)):

            if user.height and user.weight:
                height_meters = user.height / 100
                bmi = user.weight / (height_meters ** 2)
                bmi_data.append(bmi)
                dates.append(activity.date)  # Assuming activity.date contains the date information

    # ログに出力
    app.logger.info(f"get_user_bmi_data: BMI Data - {bmi_data}, Dates - {dates}")

    return bmi_data, dates


def get_user_weight_data(user_id):
    # Retrieve user weight data from the database
    weight_data = User.query.filter_by(id=user_id).with_entities(User.weight, User.date).all()

    # Extract weight and date lists
    weights = [weight for weight, _ in weight_data]
    dates = [date for _, date in weight_data]

    return weights, dates



def generate_and_save_weight_chart(user, weights, dates):
    # データベースから最新のBMIデータと日付を取得
    latest_bmi_data, latest_bmi_dates = get_user_bmi_data(user.id)
    
    # ログに出力
    app.logger.info(f"Latest BMI Data: {latest_bmi_data}")
    app.logger.info(f"Latest BMI Dates: {latest_bmi_dates}")
    
    plt.figure(figsize=(10, 6), facecolor='lightgray')  # フィギュアサイズと背景色の調整

    if weights:
        # 体重データがある場合の処理
        plt.plot(dates, weights, marker='o', linestyle='-', color='g', label='Weight')  # 色とマーカーの指定

        # 最新の体重データを取得
        latest_weight_data = UserWeight.query.filter_by(user_id=user.id).order_by(UserWeight.date).all()
        latest_weights = [weight.weight for weight in latest_weight_data]
        latest_dates = [weight.date for weight in latest_weight_data]

        # 最新の体重データをプロット
        plt.plot(latest_dates, latest_weights, marker='o', linestyle='-', color='b', label='Weight (Latest)')

        # 最新のBMIデータをプロット
        plt.plot(latest_bmi_dates, latest_bmi_data, marker='o', linestyle='-', color='r', label='BMI (Latest)')

        plt.title('Weight and BMI Progress')  # タイトルの追加
        plt.xlabel('Date')  # X軸ラベルの追加
        plt.ylabel('Value')  # Y軸ラベルの追加
        plt.legend(['Weight', 'Weight (Latest)', 'BMI (Latest)'], loc='upper right')  # 凡例の追加
        plt.grid(True, linestyle='--', alpha=0.7)  # グリッド線の追加
    else:
        # 体重データがない場合の処理
        plt.title('Weight Progress (No Data Available)')  # タイトルの追加
        plt.xlabel('Date')  # X軸ラベルの追加
        plt.ylabel('Weight (kg)')  # Y軸ラベルの追加
        plt.grid(True, linestyle='--', alpha=0.7)  # グリッド線の追加

    # 新しいグラフ画像を保存
    weight_chart_path = 'static/weight_chart.png'
    plt.savefig(weight_chart_path, bbox_inches='tight')

    # コミットが完了するまで待機
    db.session.flush()

    # 画像を読み込んでバイナリデータとして保存
    with open(weight_chart_path, 'rb') as image_file:
        image_data = BytesIO(image_file.read())
        user.dashboard_image = image_data.getvalue()

    # データベースに変更をコミット
    db.session.commit()


# /add-data ルートの例
@app.route('/add-data', methods=['POST'])
def add_data():
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()

        if user:
            # フォームからアクティビティデータと体重データを取得
            steps = int(request.form.get("steps"))
            calorie_intake = int(request.form.get("calorie_intake"))
            weight = float(request.form.get("weight"))

            # ユーザーのアクティビティデータをデータベースに追加
            new_activity = UserActivity(user_id=user.id, date=datetime.datetime.now(), steps=steps, calorie_intake=calorie_intake)
            db.session.add(new_activity)

            # ユーザーの体重データをデータベースに追加
            new_weight = UserWeight(user_id=user.id, date=datetime.datetime.now(), weight=weight)
            db.session.add(new_weight)

            # BMIを計算して更新
            user.bmi = user.calculate_bmi()

            # データベースに変更をコミット
            db.session.commit()

            # BMIデータの取得
            bmi_data, dates = get_user_bmi_data(user.id)

            # データが正しく保存されたことをログに出力
            app.logger.info(f"Activity and weight data added for user: {user.username}, Steps: {steps}, Calorie Intake: {calorie_intake}, Weight: {weight}, BMI: {user.bmi}")

            # 成功時のリダイレクトまたはレスポンスを返す
            return redirect('/dashboard')
    # ログインしていない場合の処理やエラーハンドリングを追加できます



@app.route('/add-activity', methods=['POST'])
def add_activity():
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()

        if user:
            # フォームからアクティビティデータを取得
            steps = int(request.form.get("steps"))
            calorie_intake = int(request.form.get("calorie_intake"))

            # ユーザーのアクティビティデータをデータベースに追加
            new_activity = UserActivity(user_id=user.id, date=datetime.datetime.now(), steps=steps, calorie_intake=calorie_intake)
            db.session.add(new_activity)
            db.session.commit()

            # データが正しく保存されたことをログに出力
            app.logger.info(f"Activity data added for user: {user.username}, Steps: {steps}, Calorie Intake: {calorie_intake}")

            # 成功時のリダイレクトまたはレスポンスを返す
            return redirect('/dashboard')
    # ログインしていない場合の処理やエラーハンドリングを追加できます

@app.route('/edit-profile', methods=['POST'])
def edit_profile():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            user.age = request.form.get("age")
            user.gender = request.form.get("gender")
            user.height = request.form.get("height")
            user.weight = request.form.get("weight")
            db.session.commit()
            return redirect('/profile')
    return redirect('/login-form')

@app.route('/health-data')
def health_data():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        # ユーザーの健康データをデータベースから取得
        health_data = {}  # ダミーの健康データ、実際のデータベースから取得してください
        return render_template('health_data.html', user=user, health_data=health_data)
    return redirect('/login-form')

@app.route('/add-health-data', methods=['POST'])
def add_health_data():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        if user:
            # フォームから健康データを取得し、データベースに保存
            steps = request.form.get("steps")
            calorie_intake = request.form.get("calorie_intake")
            user.steps = steps
            user.calorie_intake = calorie_intake
            user.date = datetime.datetime.now()
            db.session.commit()
            return redirect('/health-data')
    return redirect('/login-form')

@app.route('/health-goals')
def health_goals():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        # ユーザーの健康目標をデータベースから取得
        health_goal = user.health_goal
        return render_template('health_goals.html', user=user, health_goal=health_goal)
    return redirect('/login-form')

# ユーザーの健康目標をより具体的にする

@app.route('/set-health-goal', methods=['POST'])
def set_health_goal():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        # ユーザーの健康目標をデータベースから取得
        health_goal = user.health_goal

        # 目標値をMETsに変更する
        if request.form.get("new_goal") == "METs":
            health_goal = float(request.form.get("new_goal_value")) * 1000

        # 目標値を更新する
        user.health_goal = health_goal
        db.session.commit()

        return redirect('/health-goals')

    return redirect('/login-form')

# ユーザー同士で励まし合えるようなコミュニティを作成する

@app.route('/community')
def community():
    if 'username' in session:
        # ユーザーのコミュニティに参加しているかどうかをチェックする
        user = User.query.filter_by(username=session['username']).first()
        if user.community_id is not None:
            # コミュニティのページを表示する
            return render_template('community.html', community=user.community)
        else:
            # コミュニティに参加するページを表示する
            return render_template('community_join.html')

    return redirect('/login-form')

# ユーザーがコミュニティに参加する

@app.route('/community/join', methods=['POST'])
def community_join():
    if 'username' in session:
        user = User.query.filter_by(username=session['username']).first()
        # コミュニティに参加する
        user.community_id = request.form.get("community_id")
        db.session.commit()

        return redirect('/community')

    return redirect('/login-form')

# ユーザーの体重データを追加するエンドポイント
@app.route('/add-weight', methods=['POST'])
def add_weight():
    if 'username' in session:
        username = session['username']
        user = User.query.filter_by(username=username).first()

        if user:
            # フォームから体重データを取得
            weight = float(request.form.get("weight"))

            # ユーザーの体重データをデータベースに追加
            new_weight = UserWeight(user_id=user.id, date=datetime.datetime.now(), weight=weight)
            db.session.add(new_weight)
            db.session.commit()

            # BMIを計算して更新
            user.bmi = user.calculate_bmi()
            db.session.commit()

            # 成功時のリダイレクトまたはレスポンスを返す
            return redirect('/dashboard')
    # ログインしていない場合の処理やエラーハンドリングを追加できます


if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # テーブルを作成
    app.run(debug=True)