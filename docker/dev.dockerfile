FROM ubuntu:latest AS compile-image

# Setup and install Basic packages
RUN apt-get update >/dev/null && apt-get install -y -qq apt-utils
RUN apt-get update >/dev/null && \
    DEBIAN_FRONTEND="noninteractive" \
    apt-get install -y -qq --no-install-recommends \
      sudo \
      tzdata \
      build-essential \
      ca-certificates \
      ccache \
      cmake \
      curl \
      git \
      python3.12 \
      python3.12-venv \
      python3.12-dev \
      python3-pip \
      libjpeg-dev \
      libpng-dev \
    && rm -rf /var/lib/apt/lists/*

COPY install_locale.sh /install/install_locale.sh
RUN sh /install/install_locale.sh

COPY install_sshd.sh /install/install_sshd.sh
RUN sh /install/install_sshd.sh

ENV venv=/opt/venv
ARG workdir
ARG user_id
ARG group_id
ARG user_name
ARG group_name
COPY install_user.sh /install/install_user.sh
RUN sh /install/install_user.sh $venv $workdir $user_id $user_name $group_id $group_name

ARG git_name
ARG git_email
COPY install_user_git.sh /install/install_user_git.sh
RUN sh /install/install_user_git.sh "$user_name" "$git_name" "$git_email"

RUN sudo -iu $user_name python3 -m pip install gpt4all
RUN apt-get update && apt-get install -y libcudart12 libcublas12
