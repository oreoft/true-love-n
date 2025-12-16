module.exports = {
    apps: [
        {
            name: "true-love-ai",
            script: "main.py",
            cwd: __dirname,
            interpreter: "./.venv/bin/python",
            env: {APP_ENV: "prod"},
            time: true,
            log_date_format: "YYYY-MM-DD HH:mm Z"
        }
    ]
};