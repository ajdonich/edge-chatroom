# wsumfest/sport-feed:v1
CMD ["/bin/sh"]
ENV PATH=/usr/local/bin:/usr/local/sbin:/usr/local/bin:/usr/sbin:/usr/bin:/sbin:/bin
ENV LANG=C.UTF-8
RUN apk add --no-cache ca-certificates
ENV GPG_KEY=E3FF2839C048B25C084DEBE9B26995E310250568
ENV PYTHON_VERSION=3.8.3
RUN set -ex  \
	&& apk add --no-cache --virtual .fetch-deps gnupg tar xz  \
	&& wget -O python.tar.xz "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz"  \
	&& wget -O python.tar.xz.asc "https://www.python.org/ftp/python/${PYTHON_VERSION%%[a-z]*}/Python-$PYTHON_VERSION.tar.xz.asc"  \
	&& export GNUPGHOME="$(mktemp -d)"  \
	&& gpg --batch --keyserver ha.pool.sks-keyservers.net --recv-keys "$GPG_KEY"  \
	&& gpg --batch --verify python.tar.xz.asc python.tar.xz  \
	&& { command -v gpgconf > /dev/null  \
	&& gpgconf --kill all || :; }  \
	&& rm -rf "$GNUPGHOME" python.tar.xz.asc  \
	&& mkdir -p /usr/src/python  \
	&& tar -xJC /usr/src/python --strip-components=1 -f python.tar.xz  \
	&& rm python.tar.xz  \
	&& apk add --no-cache --virtual .build-deps bluez-dev bzip2-dev coreutils dpkg-dev dpkg expat-dev findutils gcc gdbm-dev libc-dev libffi-dev libnsl-dev libtirpc-dev linux-headers make ncurses-dev openssl-dev pax-utils readline-dev sqlite-dev tcl-dev tk tk-dev util-linux-dev xz-dev zlib-dev  \
	&& apk del --no-network .fetch-deps  \
	&& cd /usr/src/python  \
	&& gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"  \
	&& ./configure --build="$gnuArch" --enable-loadable-sqlite-extensions --enable-optimizations --enable-option-checking=fatal --enable-shared --with-system-expat --with-system-ffi --without-ensurepip  \
	&& make -j "$(nproc)" EXTRA_CFLAGS="-DTHREAD_STACK_SIZE=0x100000" LDFLAGS="-Wl,--strip-all"  \
	&& make install  \
	&& find /usr/local -type f -executable -not \( -name '*tkinter*' \) -exec scanelf --needed --nobanner --format '%n#p' '{}' ';' | tr ',' '\n' | sort -u | awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 { next } { print "so:" $1 }' | xargs -rt apk add --no-cache --virtual .python-rundeps  \
	&& apk del --no-network .build-deps  \
	&& find /usr/local -depth \( \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \) -exec rm -rf '{}' +  \
	&& rm -rf /usr/src/python  \
	&& python3 --version
RUN cd /usr/local/bin  \
	&& ln -s idle3 idle  \
	&& ln -s pydoc3 pydoc  \
	&& ln -s python3 python  \
	&& ln -s python3-config python-config
ENV PYTHON_PIP_VERSION=20.1.1
ENV PYTHON_GET_PIP_URL=https://github.com/pypa/get-pip/raw/eff16c878c7fd6b688b9b4c4267695cf1a0bf01b/get-pip.py
ENV PYTHON_GET_PIP_SHA256=b3153ec0cf7b7bbf9556932aa37e4981c35dc2a2c501d70d91d2795aa532be79
RUN set -ex; wget -O get-pip.py "$PYTHON_GET_PIP_URL"; echo "$PYTHON_GET_PIP_SHA256 *get-pip.py" | sha256sum -c -; python get-pip.py --disable-pip-version-check --no-cache-dir "pip==$PYTHON_PIP_VERSION" ; pip --version; find /usr/local -depth \( \( -type d -a \( -name test -o -name tests -o -name idle_test \) \) -o \( -type f -a \( -name '*.pyc' -o -name '*.pyo' \) \) \) -exec rm -rf '{}' +; rm -f get-pip.py
CMD ["python3"]
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
COPY dir:16206f45ada6377004cb7de23f32d2131b94b1bf08425a6aa6fe89b90874f8e8 in /usr/local/app
	usr/
	usr/local/
	usr/local/app/
	usr/local/app/feed/
	usr/local/app/feed/.wh..wh..opq
	usr/local/app/feed/DockerfileSport
	usr/local/app/feed/__init__.py
	usr/local/app/feed/execution_feed.py
	usr/local/app/feed/requirements.txt
	usr/local/app/feed/sport_event_feed.py
	usr/local/app/proto/
	usr/local/app/proto/.wh..wh..opq
	usr/local/app/proto/event.proto
	usr/local/app/proto/execution.proto

RUN cd feed  \
	&& mkdir gen
RUN protoc -I=proto/ --python_out=feed/gen proto/event.proto proto/execution.proto
RUN cd feed  \
	&& python3 -m pip install -r requirements.txt
WORKDIR /usr/local/app/feed
ENTRYPOINT ["python3" "sport_event_feed.py"]

