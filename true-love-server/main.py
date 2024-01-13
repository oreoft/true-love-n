import job_mgmt
import server
from configuration import Config


def main():
    # 注册并且 异步启动定时任务
    job = job_mgmt.Job()
    job.async_enable_jobs()
    # 启动http 这个留到最后启动 保活进程
    server.enable_http()


if __name__ == '__main__':
    Config()
    main()
