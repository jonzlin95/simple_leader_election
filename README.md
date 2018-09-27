```
virtualenv venv
source venv/bin/activate
pip install requirements.txt
foreman -f Procfile start
```

To simulate a network failure, you  can kill one of the python scripts --> e.g.

ps aux | grep python
kill 22379 since that will run first
