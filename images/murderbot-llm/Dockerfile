# syntax=docker/dockerfile:1
FROM nvidia/cuda:13.1.2-devel-ubuntu24.04@sha256:b9f64abf7226fdb3463ca202bc99878ec847171e6c5f77bd34c8d1403fbf1eca AS build

ARG DEBIAN_FRONTEND=noninteractive
ARG NINFER_REPO=https://github.com/dean-amer-dev/ninfer.git
ARG NINFER_REF=15700cf28b8a74999ab35cf647d436d85b00affa

RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        cmake \
        git \
        libavcodec-dev \
        libavformat-dev \
        libavutil-dev \
        libcurl4-openssl-dev \
        libswscale-dev \
        ninja-build \
        pkg-config \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /src
RUN git init -q . \
    && git remote add origin "$NINFER_REPO" \
    && git fetch -q --depth 1 origin "$NINFER_REF" \
    && git checkout -q FETCH_HEAD \
    && test "$(git rev-parse HEAD)" = "$NINFER_REF" \
    && git submodule update --init --recursive --depth 1

RUN cmake -S . -B /build -G Ninja \
        -DCMAKE_BUILD_TYPE=Release \
        -DCMAKE_CUDA_COMPILER=/usr/local/cuda/bin/nvcc \
        -DCUDAToolkit_ROOT=/usr/local/cuda \
        -DNINFER_BUILD_APPS=ON \
        -DBUILD_TESTING=OFF \
        -DNINFER_BUILD_BENCHMARKS=OFF \
    && cmake --build /build --parallel --target ninfer ninfer-serve

FROM nvidia/cuda:13.1.2-runtime-ubuntu24.04@sha256:bff001d3257971cc4752e15ac2d354befa70995ded8e141741ade50569fc192e

ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update \
    && apt-get install --yes --no-install-recommends \
        ca-certificates \
        libavcodec60 \
        libavformat60 \
        libavutil58 \
        libcurl4t64 \
        libswscale7 \
    && rm -rf /var/lib/apt/lists/*

COPY --from=build /build/apps/ninfer /usr/local/bin/ninfer
COPY --from=build /build/apps/ninfer-serve /usr/local/bin/ninfer-serve

WORKDIR /workspace
EXPOSE 8080
STOPSIGNAL SIGTERM

ENTRYPOINT ["ninfer-serve"]
CMD ["--help"]
