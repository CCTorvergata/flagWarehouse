FROM python:slim


RUN mkdir -p /flagWarehouse/client/
COPY . /flagWarehouse/client/
WORKDIR /flagWarehouse/client
RUN pip install -r /flagWarehouse/client/requirements.txt

ENV URL=
ENV API_TOKEN=
ENV USER=
ENV TYPE="ccit"

CMD python3 ./client.py -s $URL -u $USER  --type $TYPE -t $API_TOKEN -d exploits/ -v