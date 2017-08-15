

#### create bids
    screen -L docker run --rm -ti \
    --entrypoint=python \
    -v /data.nfs/CORR/:/data \
    fliem/corr:dev \
    /code/scripts/prep/02_create_onestudy_bids.py /data
