FROM python:3.8.3-alpine
ENV PROTOBUF_VERSION=3.6.1
WORKDIR /usr/local/app
RUN apk add --no-cache build-base curl automake autoconf libtool git zlib-dev
RUN mkdir -p /protobuf  \
	&& curl -L https://github.com/google/protobuf/archive/v${PROTOBUF_VERSION}.tar.gz | tar xvz --strip-components=1 -C /protobuf
RUN cd /protobuf  \
	&& autoreconf -f -i -Wall,no-obsolete  \
	&& ./configure --prefix=/usr --enable-static=no  \
	&& make -j2  \
	&& make install
RUN apk add --no-cache postgresql-dev gcc python3-dev musl-dev
COPY requirements.txt .
RUN python3 -m pip install -r requirements.txt
COPY . .
RUN protoc --python_out=. `ls proto/*.proto`
ENTRYPOINT [ "python3", "-m", "edgechat.chatservice"]
