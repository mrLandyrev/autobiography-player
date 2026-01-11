FROM python:3.13.5-slim-bullseye
RUN apt update && apt install mpc -y
WORKDIR /source
COPY requirements.txt .
RUN pip install -r requirements.txt
COPY . .
ENTRYPOINT ["fastapi", "dev", "server.py", "--host=0.0.0.0", "--port=8077"]