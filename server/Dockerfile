FROM python:3.11

WORKDIR /server

COPY requirements.txt requirements.txt
RUN pip3 install -r requirements.txt

COPY . .

EXPOSE 5555

CMD [ "bash", "run.sh"]
