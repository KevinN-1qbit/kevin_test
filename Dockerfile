FROM ubuntu:20.04
ARG HOME_DIR=/workspace
ARG DEBIAN_FRONTEND=noninteractive

RUN apt-get update && apt-get install -y \
    build-essential \
    libssl-dev \
    zlib1g-dev \
    libncurses5-dev \
    libreadline-dev \
    libsqlite3-dev \
    libgdbm-dev \
    libdb5.3-dev \
    libbz2-dev \
    libexpat1-dev \
    liblzma-dev \
    libffi-dev \
    wget \
    curl \
    cmake \
    git \
    g++ \
    python3.8 \
    python3-pip \
    autotools-dev \
    libicu-dev \
    libbz2-dev \
    libboost-all-dev \
    vim \
    && rm -rf /var/lib/apt/lists/*

RUN wget https://boostorg.jfrog.io/artifactory/main/release/1.80.0/source/boost_1_80_0.tar.gz && \
    tar xvf boost_1_80_0.tar.gz && cd boost_1_80_0 && \
    ./bootstrap.sh --prefix=/usr/ && ./b2 install

WORKDIR ${HOME_DIR}

COPY . .

