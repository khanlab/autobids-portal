FROM debian:bullseye

ENV DCM4CHE_VERSION=5.24.1

RUN apt-get update \
    && apt-get install -y -q --no-install-recommends \
        default-jre=2:1.11-72 \
        git=1:2.30.2-1 \
        python3=3.9.2-3 \
        python3-pip=20.3.4-4+deb11u1 \
        python3-setuptools=52.0.0-4 \
        unzip=6.0-26 \
        wget=1.21-1+deb11u1 \
    && rm -rf /var/lib/apt/lists/* /tmp/* /var/tmp/* \
    && pip install --upgrade --no-cache-dir pip==22.0.4 \
    && sed -i 's/TLSv1.1, //g' /etc/java-11-openjdk/security/java.security \
    && mkdir /apps

WORKDIR /apps/DicomRaw
RUN git clone https://gitlab.com/cfmm/DicomRaw . \
    && git checkout 00256d486fc790da4fa852c00cb27f42e77b1a99 \
    && pip install --no-cache-dir -r requirements.txt

WORKDIR /apps/cfmm2tar
RUN git clone https://github.com/khanlab/cfmm2tar.git . \
    && git checkout v1.0.0 \
    && chmod a+x ./*.py \
    && bash install_dcm4che_ubuntu.sh /apps/dcm4che \
    && echo '1.3.12.2.1107.5.9.1:ImplicitVRLittleEndian;ExplicitVRLittleEndian' >> /apps/dcm4che/dcm4che-${DCM4CHE_VERSION}/etc/getscu/store-tcs.properties \
    && echo 'EnhancedMRImageStorage:ImplicitVRLittleEndian;ExplicitVRLittleEndian' >> /apps/dcm4che/dcm4che-${DCM4CHE_VERSION}/etc/getscu/store-tcs.properties

WORKDIR /src
COPY . .

RUN pip install --no-cache-dir -r requirements.txt

ENV PATH=/apps/dcm4che/dcm4che-${DCM4CHE_VERSION}/bin:/apps/DicomRaw:/apps/cfmm2tar:$PATH
ENV _JAVA_OPTIONS="-Xmx2048m"

CMD ["flask", "run", "--host=0.0.0.0"]
