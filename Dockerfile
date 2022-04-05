FROM python:3.7

WORKDIR /src
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

CMD ["flask", "run", "--host=0.0.0.0"]
