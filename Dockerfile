FROM ubuntu:20.04
ARG HOME_DIR=/workspace
ARG DEBIAN_FRONTEND=noninteractive

# Install dependencies 
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

WORKDIR ${HOME_DIR}
COPY . .

# Build and compile C++ files
WORKDIR ${HOME_DIR}/Trillium/src/cpp_compiler
RUN cmake . 
RUN make

# Install Trillium package
WORKDIR ${HOME_DIR}
RUN pip install -e .

WORKDIR ${HOME_DIR}/Trillium

