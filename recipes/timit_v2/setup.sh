
#######################################################################
# Site specific configuration. Override these settings to run on
# you system.

hostname=$(hostname -f)
if [[ "$hostname" == *".fit.vutbr.cz" ]]; then
    timit=/mnt/matylda2/data/TIMIT/timit
    server=matylda5
    parallel_env=sge
    parallel_opts="-l mem_free=200M,ram_free=200M,$server=1"
    parallel_opts_gpu="-l gpu=1,mem_free=1G,ram_free=1G"
elif [[ "$hostname" = *"clsp.jhu.edu" ]]; then
    timit=/export/corpora5/LDC/LDC93S1/timit/TIMIT
    parallel_env=sge
    parallel_opts="-l mem_free=200M,ram_free=200M,hostname=b*|c*"
    parallel_opts_gpu="-l gpu=1,mem_free=1G,ram_free=1G,hostname=b1[123456789]*|c*"
else
    echo "Unkown location configuration. Please update the"
    echo "\"setup.sh\" file."
    exit 1
fi


#######################################################################
# Directory structure.

confdir=$(pwd)/conf
datadir=$(pwd)/data
langdir=$datadir/lang
expdir=$(pwd)/exp


#######################################################################
# Features extraction.

fea_njobs=10
fea_parallel_opts="$parallel_opts"
fea_conf=$confdir/features.yml


#######################################################################
# HMM-GMM model parameters.

hmm_emission_conf=$confdir/hmm_gmm/hmm.yml
hmm_dir=$expdir/hmm_gmm
hmm_align_njobs=20
hmm_align_parallel_opts="$parallel_opts"
hmm_align_iters="1 2 3 4 5 6 7 8 9 10 12 14 16 18 20 23 26 29"
hmm_train_iters=30
hmm_train_emissions_lrate=0.1
hmm_train_emissions_batch_size=400
hmm_train_emissions_epochs=10
hmm_train_emissions_opts="--fast-eval --use-gpu"
hmm_train_parallel_opts="$parallel_opts_gpu"
hmm_decode_njobs=2
hmm_decode_parallel_opts="$parallel_opts"



#######################################################################
# VAE-HMM model.

vae_hmm_confdir=$confdir/vae_hmm
vae_hmm_dir=$expdir/vae_hmm
vae_hmm_encoder_conf=$vae_hmm_confdir/encoder.yml
vae_hmm_decoder_conf=$vae_hmm_confdir/decoder.yml
vae_hmm_nflow_conf=$vae_hmm_confdir/normalizing_flow.yml
vae_hmm_nnet_width=512
vae_hmm_latent_dim=30
vae_hmm_hmm_conf=$vae_hmm_confdir/hmm.yml
vae_hmm_encoder_cov_type=isotropic
vae_hmm_decoder_cov_type=diagonal
vae_hmm_align_njobs=20
vae_hmm_align_parallel_opts="$parallel_opts"
vae_hmm_align_iters="2 3 4 5 6 7 8 9 10 11 12 13 14 15 16 17 18 19 20"
vae_hmm_train_iters=20
vae_hmm_train_epochs_per_iter=50
vae_hmm_train_warmup_iters=0
vae_hmm_train_lrate=1e-1
vae_hmm_train_nnet_lrate=1e-3
vae_hmm_train_batch_size=400
vae_hmm_train_opts="--fast-eval --use-gpu"
vae_hmm_train_parallel_opts="$parallel_opts_gpu"


#######################################################################
# AUD (HMM) model parameters.

aud_hmm_conf=$confdir/aud_hmm/hmm.yml
aud_hmm_dir=$expdir/aud_hmm
aud_hmm_n_units=100
aud_hmm_lm_concentration=1.
aud_hmm_align_njobs=20
aud_hmm_align_parallel_opts="$parallel_opts"
aud_hmm_align_iters="1 2 3 4 5 6 7 8 9 10 12 14 16 18 20 23 26 29"
aud_hmm_train_iters=30
aud_hmm_train_emissions_lrate=0.1
aud_hmm_train_emissions_batch_size=400
aud_hmm_train_emissions_epochs=10
aud_hmm_train_emissions_opts="--fast-eval --use-gpu"
aud_hmm_train_parallel_opts="$parallel_opts_gpu"
aud_hmm_decode_njobs=2
aud_hmm_decode_parallel_opts="$parallel_opts"


#######################################################################
# Score options.

remove_sym="" # Support multiple symbol, e.g. "sil spn nsn"
duplicate="no" # Do not allow adjacent duplicated phones. Only effective at scoring stage.
phone_48_to_39_map=$langdir/phones_48_to_39.txt

