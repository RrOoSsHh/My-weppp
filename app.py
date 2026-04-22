from flask import Flask, render_template, request, jsonify
import requests
import time
import threading
import json

app = Flask(__name__)

class Colors:
    HEADER = '\033[95m'
    BLUE = '\033[94m'
    CYAN = '\033[96m'
    GREEN = '\033[92m'
    WARNING = '\033[93m'
    FAIL = '\033[91m'
    ENDC = '\033[0m'
    BOLD = '\033[1m'
    WHITE = '\033[97m'

all_reports = {
    "1": {"code": '["adult_content-nudity_or_sexual_activity"]', "name": "Nudity or Sexual Activity"},
    "2": {"code": '["violence_hate_or_exploitation-sexual_exploitation-yes"]', "name": "Sexual Exploitation (Under 18)"},
    "3": {"code": '["adult_content-threat_to_share_nude_images-u18-yes"]', "name": "Threat to Share Nude Images (Under 18)"},
    "4": {"code": '["suicide_or_self_harm_concern-suicide_or_self_injury"]', "name": "Suicide or Self Injury"},
    "5": {"code": '["ig_scam_financial_investment"]', "name": "Financial Scam"},
    "6": {"code": '["selling_or_promoting_restricted_items-drugs-high-risk"]', "name": "High Risk Drugs"},
    "7": {"code": '["violent_hateful_or_disturbing-credible_threat"]', "name": "Credible Threat"},
    "8": {"code": '["suicide_or_self_harm_concern-eating_disorder"]', "name": "Eating Disorder"},
    "9": {"code": '["harrassment_or_abuse-harassment-me-u18-yes"]', "name": "Harassment (Me)"},
    "10": {"code": '["ig_spam_v3"]', "name": "Spam"},
    "11": {"code": '["ig_user_impersonation"]', "name": "Impersonation"},
    "12": {"code": '["ig_its_inappropriate"]', "name": "Inappropriate"},
    "13": {"code": '["violent_hateful_or_disturbing-violence"]', "name": "Violence"},
    "14": {"code": '["violent_hateful_or_disturbing-promotes_hate-hate_speech_or_symbols"]', "name": "Hate Speech"}
}

headers = {
    'User-Agent': "Mozilla/5.0 (Linux; Android 9; SH-M24 Build/PQ3A.190705.09121607; wv) AppleWebKit/537.36 (KHTML, like Gecko) Version/4.0 Chrome/124.0.6367.82 Safari/537.36 InstagramLite 1.0.0.0.145 Android (28/9; 240dpi; 900x1600; AQUOS; SH-M24; gracelte; qcom; ar_EG; 115357035)",
    'sec-ch-ua': '"Chromium";v="124", "Android WebView";v="124", "Not-A.Brand";v="99"',
    'x-ig-www-claim': "hmac.AR3_rYnLKeBezIQYHfIUtjIcljl6VzAqGT8JGhQ_M0eCdWOV",
    'x-web-session-id': "m3n2go:suujxi:8c53jj",
    'sec-ch-ua-platform-version': '"9.0.0"',
    'x-requested-with': "XMLHttpRequest",
    'x-csrftoken': "FxCF6jR5tSy3wdcZCfRIZN5viVxZmV1k",
    'x-ig-app-id': "936619743392459",
    'origin': "https://www.instagram.com",
    'referer': "https://www.instagram.com/",
    'accept-language': "ar-EG,ar;q=0.9,en-US;q=0.8,en;q=0.7",
}

def send_report(session_id, target_id, report_code):
    """إرسال بلاغ واحد مع التحقق من النجاح عبر JSON"""
    cookies = {'sessionid': session_id, 'csrftoken': 'FxCF6jR5tSy3wdcZCfRIZN5viVxZmV1k'}
    
    # الخطوة 1: جلب context
    url_context = "https://www.instagram.com/api/v1/web/reports/get_frx_prompt/"
    data_context = {
        'container_module': 'profilePage',
        'entry_point': '1',
        'location': '2',
        'object_id': target_id,
        'object_type': '5',
        'frx_prompt_request_type': '1',
    }
    try:
        resp = requests.post(url_context, cookies=cookies, headers=headers, data=data_context, timeout=10)
        if resp.status_code != 200:
            return False
        context = resp.json().get('response', {}).get('context')
        if not context:
            return False
    except Exception as e:
        print(f"Error getting context: {e}")
        return False

    # الخطوة 2: إرسال البلاغ
    payload = {
        'container_module': "profilePage",
        'entry_point': "1",
        'location': "2",
        'object_id': target_id,
        'object_type': "5",
        'context': context,
        'selected_tag_types': report_code,
        'frx_prompt_request_type': "2",
        'jazoest': "22816"
    }
    url_report = "https://www.instagram.com/api/v1/web/reports/get_frx_prompt/"
    try:
        response = requests.post(url_report, data=payload, headers=headers, cookies=cookies, timeout=10)
        if response.status_code == 200:
            # التحقق من JSON بدلاً من النص
            try:
                resp_json = response.json()
                if resp_json.get('status') == 'ok':
                    return True
            except:
                # إذا لم يكن JSON، نتحقق من النص كحل احتياطي
                if '"status":"ok"' in response.text:
                    return True
        return False
    except Exception as e:
        print(f"Error sending report: {e}")
        return False

# متغيرات عالمية لتتبع التشغيل
bot_running = False
bot_thread = None
stats = {"success": 0, "failed": 0, "last_status": "Idle", "target_id": "", "report_name": ""}

def run_bot_loop(session_id, target_id, report_code, interval, repeats, report_name):
    global bot_running, stats
    stats = {"success": 0, "failed": 0, "last_status": "Started", "target_id": target_id, "report_name": report_name}
    count = 0
    
    # اختبار أولي: هل يمكن جلب context بنجاح؟
    test_cookies = {'sessionid': session_id, 'csrftoken': 'FxCF6jR5tSy3wdcZCfRIZN5viVxZmV1k'}
    test_url = "https://www.instagram.com/api/v1/web/reports/get_frx_prompt/"
    test_data = {
        'container_module': 'profilePage',
        'entry_point': '1',
        'location': '2',
        'object_id': target_id,
        'object_type': '5',
        'frx_prompt_request_type': '1',
    }
    try:
        test_resp = requests.post(test_url, cookies=test_cookies, headers=headers, data=test_data, timeout=10)
        if test_resp.status_code != 200:
            stats["last_status"] = "Failed: Invalid session or target ID"
            bot_running = False
            return
    except:
        stats["last_status"] = "Failed: Network error"
        bot_running = False
        return

    # الحلقة الرئيسية
    while bot_running and (repeats == 0 or count < repeats):
        success = send_report(session_id, target_id, report_code)
        if success:
            stats["success"] += 1
            stats["last_status"] = f"✅ Report sent ({stats['success']} total)"
        else:
            stats["failed"] += 1
            stats["last_status"] = f"❌ Failed ({stats['failed']} total)"
        count += 1
        
        if bot_running and (repeats == 0 or count < repeats):
            time.sleep(interval)
    
    # إعادة تعيين bot_running بعد انتهاء الحلقة تلقائياً
    bot_running = False
    if repeats != 0 and count >= repeats:
        stats["last_status"] = f"Finished: {stats['success']} success, {stats['failed']} failed"
    else:
        stats["last_status"] = "Stopped by user"

@app.route('/')
def index():
    return render_template('index.html', reports=all_reports)

@app.route('/start', methods=['POST'])
def start():
    global bot_running, bot_thread
    if bot_running:
        return jsonify({"status": "already_running"})
    
    data = request.json
    session_id = data.get('session_id', '').strip()
    target_id = data.get('target_id', '').strip()
    report_key = data.get('report_key', '10')
    
    # معالجة الأعداد مع fallback
    try:
        interval = int(data.get('interval', 5))
        if interval < 1:
            interval = 1
    except:
        interval = 5
    
    try:
        repeats = int(data.get('repeats', 1))
        if repeats < 0:
            repeats = 0
    except:
        repeats = 1
    
    if not session_id or not target_id:
        return jsonify({"status": "error", "message": "Session ID and Target ID are required"})
    
    report_info = all_reports.get(report_key)
    if not report_info:
        return jsonify({"status": "error", "message": "Invalid report type"})
    
    report_code = report_info['code']
    report_name = report_info['name']
    
    bot_running = True
    bot_thread = threading.Thread(
        target=run_bot_loop,
        args=(session_id, target_id, report_code, interval, repeats, report_name)
    )
    bot_thread.daemon = True
    bot_thread.start()
    return jsonify({"status": "started"})

@app.route('/stop', methods=['POST'])
def stop():
    global bot_running
    bot_running = False
    return jsonify({"status": "stopped"})

@app.route('/status', methods=['GET'])
def status():
    global stats, bot_running
    return jsonify({
        "running": bot_running,
        "success": stats["success"],
        "failed": stats["failed"],
        "last_status": stats["last_status"],
        "target_id": stats.get("target_id", ""),
        "report_name": stats.get("report_name", "")
    })

if __name__ == '__main__':
    # مناسب لاستضافة Pella (وربما تستخدم منفذ 5000 أو المنفذ المخصص)
    app.run(debug=False, host='0.0.0.0', port=5000)