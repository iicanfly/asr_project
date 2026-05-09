import subprocess
import sys
import os
import ipaddress


def generate_cert(server_ip=None):
    cert_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'cert')
    os.makedirs(cert_dir, exist_ok=True)
    cert_path = os.path.join(cert_dir, 'cert.pem')
    key_path = os.path.join(cert_dir, 'key.pem')

    try:
        from cryptography import x509
        from cryptography.x509.oid import NameOID
        from cryptography.hazmat.primitives import hashes, serialization
        from cryptography.hazmat.primitives.asymmetric import rsa
        import datetime

        if server_ip is None:
            server_ip = sys.argv[1] if len(sys.argv) > 1 else "0.0.0.0"

        key = rsa.generate_private_key(public_exponent=65537, key_size=2048)

        subject = issuer = x509.Name([
            x509.NameAttribute(NameOID.COMMON_NAME, 'VoiceSystem'),
            x509.NameAttribute(NameOID.ORGANIZATION_NAME, 'VoiceSystem'),
        ])

        san_list = [
            x509.DNSName('localhost'),
            x509.IPAddress(ipaddress.IPv4Address('127.0.0.1')),
        ]
        try:
            san_list.append(x509.IPAddress(ipaddress.IPv4Address(server_ip)))
        except ipaddress.AddressValueError:
            san_list.append(x509.DNSName(server_ip))

        san = x509.SubjectAlternativeName(san_list)

        cert = (
            x509.CertificateBuilder()
            .subject_name(subject)
            .issuer_name(issuer)
            .public_key(key.public_key())
            .serial_number(x509.random_serial_number())
            .not_valid_before(datetime.datetime.utcnow())
            .not_valid_after(datetime.datetime.utcnow() + datetime.timedelta(days=3650))
            .add_extension(san, critical=False)
            .sign(key, hashes.SHA256())
        )

        with open(cert_path, 'wb') as f:
            f.write(cert.public_bytes(serialization.Encoding.PEM))
        with open(key_path, 'wb') as f:
            f.write(key.private_bytes(
                serialization.Encoding.PEM,
                serialization.PrivateFormat.TraditionalOpenSSL,
                serialization.NoEncryption()
            ))

        print(f"SSL 证书生成成功！")
        print(f"  证书文件: {cert_path}")
        print(f"  私钥文件: {key_path}")
        print(f"  服务器 IP: {server_ip}")
        print(f"  注意：自签名证书不被浏览器信任，首次访问时需要点击「高级」->「继续前往」")

    except ImportError:
        print("缺少 cryptography 库，正在安装...")
        subprocess.check_call([sys.executable, '-m', 'pip', 'install', 'cryptography'])
        print("安装完成，请重新运行此脚本")


if __name__ == '__main__':
    generate_cert()
