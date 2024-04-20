FROM python:slim


RUN mkdir -p /flagWarehouse/client/
COPY . /flagWarehouse/client/
WORKDIR /flagWarehouse/client
RUN pip install -r /flagWarehouse/client/requirements.txt

ENV URL=
ENV API_TOKEN=

CMD python3 ./client.py -s $URL -u prod -t $API_TOKEN -d exploits/