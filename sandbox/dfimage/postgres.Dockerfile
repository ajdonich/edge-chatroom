# postgres:alpine
CMD ["/bin/sh"]
RUN set -eux; addgroup -g 70 -S postgres; adduser -u 70 -S -D -G postgres -H -h /var/lib/postgresql -s /bin/sh postgres; mkdir -p /var/lib/postgresql; chown -R postgres:postgres /var/lib/postgresql
ENV LANG=en_US.utf8
RUN mkdir /docker-entrypoint-initdb.d
ENV PG_MAJOR=12
ENV PG_VERSION=12.3
ENV PG_SHA256=94ed64a6179048190695c86ec707cc25d016056ce10fc9d229267d9a8f1dcf41
RUN set -ex  \
	&& wget -O postgresql.tar.bz2 "https://ftp.postgresql.org/pub/source/v$PG_VERSION/postgresql-$PG_VERSION.tar.bz2"  \
	&& echo "$PG_SHA256 *postgresql.tar.bz2" | sha256sum -c -  \
	&& mkdir -p /usr/src/postgresql  \
	&& tar --extract --file postgresql.tar.bz2 --directory /usr/src/postgresql --strip-components 1  \
	&& rm postgresql.tar.bz2  \
	&& apk add --no-cache --virtual .build-deps bison coreutils dpkg-dev dpkg flex gcc libc-dev libedit-dev libxml2-dev libxslt-dev linux-headers llvm10-dev clang g++ make openssl-dev perl-utils perl-ipc-run util-linux-dev zlib-dev icu-dev  \
	&& cd /usr/src/postgresql  \
	&& awk '$1 == "#define"  \
	&& $2 == "DEFAULT_PGSOCKET_DIR"  \
	&& $3 == "\"/tmp\"" { $3 = "\"/var/run/postgresql\""; print; next } { print }' src/include/pg_config_manual.h > src/include/pg_config_manual.h.new  \
	&& grep '/var/run/postgresql' src/include/pg_config_manual.h.new  \
	&& mv src/include/pg_config_manual.h.new src/include/pg_config_manual.h  \
	&& gnuArch="$(dpkg-architecture --query DEB_BUILD_GNU_TYPE)"  \
	&& wget -O config/config.guess 'https://git.savannah.gnu.org/cgit/config.git/plain/config.guess?id=7d3d27baf8107b630586c962c057e22149653deb'  \
	&& wget -O config/config.sub 'https://git.savannah.gnu.org/cgit/config.git/plain/config.sub?id=7d3d27baf8107b630586c962c057e22149653deb'  \
	&& ./configure --build="$gnuArch" --enable-integer-datetimes --enable-thread-safety --enable-tap-tests --disable-rpath --with-uuid=e2fs --with-gnu-ld --with-pgport=5432 --with-system-tzdata=/usr/share/zoneinfo --prefix=/usr/local --with-includes=/usr/local/include --with-libraries=/usr/local/lib --with-openssl --with-libxml --with-libxslt --with-icu --with-llvm  \
	&& make -j "$(nproc)" world  \
	&& make install-world  \
	&& make -C contrib install  \
	&& runDeps="$( scanelf --needed --nobanner --format '%n#p' --recursive /usr/local | tr ',' '\n' | sort -u | awk 'system("[ -e /usr/local/lib/" $1 " ]") == 0 { next } { print "so:" $1 }' )"  \
	&& apk add --no-cache --virtual .postgresql-rundeps $runDeps bash su-exec tzdata  \
	&& apk del --no-network .build-deps  \
	&& cd /  \
	&& rm -rf /usr/src/postgresql /usr/local/share/doc /usr/local/share/man  \
	&& find /usr/local -name '*.a' -delete
RUN sed -ri "s!^#?(listen_addresses)\s*=\s*\S+.*!\1 = '*'!" /usr/local/share/postgresql/postgresql.conf.sample
RUN mkdir -p /var/run/postgresql  \
	&& chown -R postgres:postgres /var/run/postgresql  \
	&& chmod 2777 /var/run/postgresql
ENV PGDATA=/var/lib/postgresql/data
RUN mkdir -p "$PGDATA"  \
	&& chown -R postgres:postgres "$PGDATA"  \
	&& chmod 777 "$PGDATA"
VOLUME [/var/lib/postgresql/data]
COPY file:33e6fc6ab9ea2b87183e496ad72f1df7f682913ffd781b1451fd178b0c7d745a in /usr/local/bin/
	usr/
	usr/local/
	usr/local/bin/
	usr/local/bin/docker-entrypoint.sh

ENTRYPOINT ["docker-entrypoint.sh"]
EXPOSE 5432
CMD ["postgres"]

