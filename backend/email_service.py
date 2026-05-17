import aiosmtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

from config import SMTP_HOST, SMTP_PORT, SMTP_USER, SMTP_PASSWORD, SMTP_FROM


async def send_verification_code(to_email: str, code: str, code_type: str) -> bool:
    """发送验证码邮件"""
    subject = "注册验证码" if code_type == "register" else "密码重置验证码"

    html_body = f"""
    <div style="max-width:480px;margin:0 auto;font-family:-apple-system,BlinkMacSystemFont,'Segoe UI',Roboto,sans-serif;padding:32px;background:#faf9f7;border-radius:16px;">
      <div style="text-align:center;margin-bottom:24px;">
        <h2 style="color:#1a1916;margin:0;font-size:20px;">老薛的技术博客</h2>
        <p style="color:#74716b;font-size:13px;margin-top:4px;">Anders' TechBlog</p>
      </div>
      <div style="background:#ffffff;border:1px solid #ebe8e1;border-radius:12px;padding:24px;text-align:center;">
        <p style="color:#74716b;font-size:14px;margin:0 0 16px;">
          您的{subject}为：
        </p>
        <div style="font-size:32px;font-weight:700;letter-spacing:8px;color:#c96442;font-family:monospace;">
          {code}
        </div>
        <p style="color:#989590;font-size:12px;margin-top:16px;">
          验证码 10 分钟内有效，请勿泄露给他人
        </p>
      </div>
      <p style="color:#b3b0a8;font-size:11px;text-align:center;margin-top:20px;">
        如果这不是您的操作，请忽略此邮件
      </p>
    </div>
    """

    message = MIMEMultipart("alternative")
    message["From"] = SMTP_FROM
    message["To"] = to_email
    message["Subject"] = subject
    message.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        await aiosmtplib.send(
            message,
            hostname=SMTP_HOST,
            port=SMTP_PORT,
            username=SMTP_USER,
            password=SMTP_PASSWORD,
            use_tls=True,
        )
        return True
    except Exception as e:
        print(f"邮件发送失败: {e}")
        return False
