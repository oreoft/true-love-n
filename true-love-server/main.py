import server
from configuration import Config


def main():
    # 启动http 这个留到最后启动 保活进程
    server.enable_http()


if __name__ == '__main__':
    Config()
    main()
