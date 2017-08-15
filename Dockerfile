FROM bids/base_validator:latest


RUN sudo apt-get update && apt-get install -y tree htop unzip wget

# Install anaconda
RUN echo 'export PATH=/usr/local/anaconda:$PATH' > /etc/profile.d/conda.sh && \
    wget --quiet https://repo.continuum.io/archive/Anaconda3-4.2.0-Linux-x86_64.sh -O anaconda.sh && \
    /bin/bash anaconda.sh -b -p /usr/local/anaconda && \
    rm anaconda.sh

ENV PATH=/usr/local/anaconda/bin:$PATH

RUN pip install pybids
RUN pip install duecredit


COPY . /code/


#ENTRYPOINT ["/bin/bash"]
