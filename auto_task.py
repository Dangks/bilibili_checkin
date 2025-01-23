import requests
import json
import time
import os
import sys
from datetime import datetime, timedelta, timezone
from loguru import logger
import qrcode
import io
from PIL import Image

# 配置日志
class BeijingFormatter:
    @staticmethod
    def format(record):
        dt = datetime.fromtimestamp(record["time"].timestamp(), tz=timezone.utc)
        local_dt = dt + timedelta(hours=8)
        record["extra"]["local_time"] = local_dt.strftime('%H:%M:%S,%f')[:-3]
        return "{time:YYYY-MM-DD HH:mm:ss,SSS}(CST {extra[local_time]}) - {level} - {message}\n"

logger.remove()
logger.add(sys.stdout, format=BeijingFormatter.format, level="INFO", colorize=True)

class BilibiliTask:
    def display_qrcode(self, url):
        """生成并显示二维码"""
        try:
            # 生成二维码
            qr = qrcode.QRCode(
                version=1,
                box_size=10,
                border=5
            )
            qr.add_data(url)
            qr.make(fit=True)
            
            # 创建二维码图片
            qr_image = qr.make_image(fill_color="black", back_color="white")
            
            # 保存二维码图片
            qr_image.save("login_qr.png")
            
            # 在Windows系统下打开二维码图片
            os.system("start login_qr.png")
            
            return True
        except Exception as e:
            logger.error(f"生成二维码失败: {str(e)}")
            return False
        
    def generate_qrcode(self):
        """获取登录二维码"""
        try:
            res = requests.get(
                'https://passport.bilibili.com/x/passport-login/web/qrcode/generate',
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
            )
            if res.status_code != 200:
                return None, None
                
            data = res.json()
            if data['code'] != 0:
                return None, None
                
            return data['data']['url'], data['data']['qrcode_key']
        except Exception as e:
            logger.error(f"获取二维码失败: {str(e)}")
            return None, None

    def check_qrcode_status(self, qrcode_key):
        """检查二维码扫描状态"""
        try:
            data = {
                'qrcode_key': qrcode_key
            }
            res = requests.get(
                'https://passport.bilibili.com/x/passport-login/web/qrcode/poll',
                params=data,
                headers={'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0'}
            )
            if res.status_code != 200:
                return None
                
            return res.json()
        except Exception as e:
            logger.error(f"检查扫码状态失败: {str(e)}")
            return None

    def login_by_qrcode(self):
        """扫码登录"""
        qr_url, qrcode_key = self.generate_qrcode()
        if not qr_url or not qrcode_key:
            return False, "获取二维码失败"
            
        # 显示二维码
        if not self.display_qrcode(qr_url):
            return False, "生成二维码失败"
            
        logger.info("二维码已生成，请使用哔哩哔哩手机APP扫描登录")
        
        for _ in range(120):  # 等待2分钟
            status = self.check_qrcode_status(qrcode_key)
            if not status:
                time.sleep(1)
                continue
                
            if status['code'] == 0:
                data = status['data']
                if data['code'] == 0:
                    try:
                        # 保存完整的响应数据
                        with open('auth.json', 'w', encoding='utf-8') as f:
                            json.dump(status, f, ensure_ascii=False, indent=2)
                        
                        # 提取并保存 cookie
                        cookies = []
                        # 修改这里: 直接使用url中的参数作为cookie
                        if 'url' in data:
                            params = data['url'].split('?')[1].split('&')
                            for param in params:
                                key, value = param.split('=')
                                cookies.append(f"{key}={value}")
                        
                        cookie_str = '; '.join(cookies)
                        
                        with open('cookie.txt', 'w', encoding='utf-8') as f:
                            f.write(cookie_str)
                            
                        self.cookie = cookie_str
                        self.headers['Cookie'] = cookie_str
                        return True, None
                    except Exception as e:
                        logger.error(f"解析认证信息失败: {str(e)}")
                        return False, f"保存认证信息失败: {str(e)}"
                elif data['code'] == 86038:
                    return False, "二维码已过期"
                elif data['code'] == 86090:
                    logger.info("等待扫码确认...")
                    
            time.sleep(1)
            
        return False, "二维码已过期"

    def __init__(self, cookie):
        self.cookie = cookie
        self.headers = {
            'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/120.0.0.0',
            'Accept': 'application/json, text/plain, */*',
            'Cookie': cookie
        }
        
        # 如果存在cookie文件则加载
        if not cookie and os.path.exists('cookie.txt'):
            try:
                with open('cookie.txt', 'r', encoding='utf-8') as f:
                    self.cookie = f.read().strip()
                    self.headers['Cookie'] = self.cookie
            except Exception as e:
                logger.error(f"加载cookie失败: {str(e)}")
        
    def get_csrf(self):
        """从cookie获取csrf"""
        for item in self.cookie.split(';'):
            if item.strip().startswith('bili_jct'):
                return item.split('=')[1]
        return None

    def check_login_status(self):
        """检查登录状态"""
        try:
            res = requests.get('https://api.bilibili.com/x/web-interface/nav', headers=self.headers)
            if res.json()['code'] == -101:
                return False, '账号未登录'
            return True, None
        except Exception as e:
            return False, str(e)
        
    def share_video(self):
        """分享视频"""
        try:
            # 获取随机视频
            res = requests.get('https://api.bilibili.com/x/web-interface/dynamic/region?ps=1&rid=1', headers=self.headers)
            bvid = res.json()['data']['archives'][0]['bvid']
            
            # 分享视频
            data = {
                'bvid': bvid,
                'csrf': self.get_csrf()
            }
            res = requests.post('https://api.bilibili.com/x/web-interface/share/add', headers=self.headers, data=data)
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def watch_video(self, bvid):
        """观看视频"""
        try:
            data = {
                'bvid': bvid,
                'csrf': self.get_csrf(),
                'played_time': '2'
            }
            res = requests.post('https://api.bilibili.com/x/click-interface/web/heartbeat', 
                              headers=self.headers, data=data)
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def live_sign(self):
        """直播签到"""
        try:
            res = requests.get('https://api.live.bilibili.com/xlive/web-ucenter/v1/sign/DoSign',
                             headers=self.headers)
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def manga_sign(self):
        """漫画签到"""
        try:
            res = requests.post('https://manga.bilibili.com/twirp/activity.v1.Activity/ClockIn',
                              headers=self.headers,
                              data={'platform': 'ios'})
            if res.json()['code'] == 0:
                return True, None
            else:
                return False, res.json().get('message', '未知错误')
        except Exception as e:
            return False, str(e)
            
    def get_user_info(self):
        """获取用户信息"""
        try:
            res = requests.get('https://api.bilibili.com/x/web-interface/nav',
                             headers=self.headers)
            data = res.json()['data']
            return {
                'uname': data['uname'],
                'uid': data['mid'],
                'level': data['level_info']['current_level'],
                'exp': data['level_info']['current_exp'],
                'coin': data['money']
            }
        except:
            return None

def log_info(tasks, user_info):
    """记录任务和用户信息的日志"""
    print('=== 任务完成情况 ===')
    for name, (success, message) in tasks.items():
        if success:
            logger.info(f'{name}: 成功')
        else:
            logger.error(f'{name}: 失败，原因: {message}')
        
    if user_info:
        print('\n=== 用户信息 ===')
        print(f'用户名: {user_info["uname"][0]}{"*" * (len(user_info["uname"]) - 1)}')
        print(f'UID: {str(user_info["uid"])[:2]}{"*" * (len(str(user_info["uid"])) - 4)}{str(user_info["uid"])[-2:]}')
        print(f'等级: {user_info["level"]}')
        print(f'经验: {user_info["exp"]}')
        print(f'硬币: {user_info["coin"]}')

def main():
    # 从环境变量获取cookie
    cookie = os.environ.get('BILIBILI_COOKIE')
    
    bili = BilibiliTask(cookie if cookie else '')
    
    # 如果环境变量中没有cookie,则尝试扫码登录
    if not cookie:
        logger.info("未找到cookie,开始扫码登录...")
        login_status, message = bili.login_by_qrcode()
        if not login_status:
            logger.error(f'扫码登录失败: {message}')
            sys.exit(1)
        logger.info("扫码登录成功!")
    
    # 验证登录状态    
    status, message = bili.check_login_status()
    if not status:
        logger.error(f'登录验证失败: {message}')
        sys.exit(1)
    
    # 执行每日任务
    tasks = {
        '分享视频': bili.share_video(),
        '观看视频': bili.watch_video('BV1rtkiYUEvy'),  # 观看任意一个视频
        '直播签到': bili.live_sign(),
        '漫画签到': bili.manga_sign()
    }
    
    # 获取用户信息
    user_info = bili.get_user_info()
    
    # 记录日志
    log_info(tasks, user_info)

if __name__ == '__main__':
    main()