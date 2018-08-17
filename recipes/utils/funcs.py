

import torch
import os
import sys


def create_48_39_phone_map(phone_48_to_39):
    '''
    Create a mapping between 48 phones and 39 phones. (For timit only)
    Args: 
        phone_48_to_39(str): mapping file
    Returns:
        dict_phone_map: phone_48(str) -> phone_39(str)
    '''
    dict_phone_map = {}
    with open(phone_48_to_39, 'r') as f:
        for l in f:
            l = l.strip()
            l = l.split()
            dict_phone_map[l[0]] = l[1]
    return dict_phone_map

def create_phone_dict(phonefile, nstate_per_phone):
    '''Create phone_id dictionary and state to phone dictionary
    Args:
        phonefile(str): with list of phonemes
        nstate_per_phone(int)
    Returns:
        dict_phones: phone(str) -> phone_id(int)
        dict_state_to_phone: state_id(int) -> phoneme(str)
    '''
    with open(phonefile, 'r') as p:
        phonelist = [l.rstrip('\n') for l in p]
    dict_phone_ids = {}
    dict_state_to_phone = {}
    for i, j in enumerate(phonelist):
        dict_phone_ids[j] = i
        for u in range(nstate_per_phone):
            dict_state_to_phone[nstate_per_phone * i + u] = j
    return dict_phone_ids, dict_state_to_phone

def convert_state_to_phone(dict_state_to_phone, states, nstates_per_phone):
    '''Convert state sequence into phone sequence
    Args:
        dict_state_to_phone: state_id(int) -> phoneme(str)
        states: list of state ids(int)
        nstates_per_phone(int)
    Return:
        phones: list of phonemes(str)
    '''
    phones = []
    ending = [i + nstates_per_phone - 1 for i in
    dict_state_to_phone.keys() if i % nstates_per_phone == 0]
    for i in range(len(states) - 1):
        if (states[i] != states[i+1]) and (states[i]) in ending:
            phones.append(dict_state_to_phone[states[i]])
    phones.append(dict_state_to_phone[states[-1]])
    return phones

def score(dict_ref, dict_hyp, details=False):
    '''Compute error rate given reference and hypothesis using DTW
    Args: dict_ref: uttid(str) -> list of phonemes(str)
          dict_hyp: uttid(str) -> list of phonemes(str)
          details: Print each utterance error details
    Returns:
         Total error rate.
    '''
    # Per utterance error detail(ins, del, sub) not implemented
    tot_len = 0
    tot_err = 0
    #tot_det = torch.zeros(3)
    for k in dict_ref.keys():
        ref = dict_ref[k]
        hyp = dict_hyp[k]
        det = torch.zeros(3)
        mtrix = torch.zeros((len(hyp) + 1, len(ref) + 1))
        for i in range(len(ref) + 1):
            mtrix[0, i] = i
        for i in range(len(hyp) + 1):
            mtrix[i, 0] = i
        for i in range(1, len(ref) + 1):
            for j in range(1, len(hyp) + 1):
                ins_err = mtrix[j-1, i] + 1
                del_err = mtrix[j, i-1] + 1
                sub_err = mtrix[j-1, i-1] + int(ref[i - 1] != hyp[j - 1])
                err = [ins_err, del_err, sub_err]
                mtrix[j, i] = min(err)
        #if details:
        #    None
            # Not finished to print details for each utt
        #tot_det += det        
        tot_err += mtrix[-1, -1]
        tot_len += len(ref)
    return (tot_err / tot_len)

def read_transcription(trans_file):
    '''Read transcription file in text and save into phone id sequences.
    Args:
        trans_file(str): transcription file in phoneme sequences
    Return:
        dict_trans: uttid(str) -> list of phonemes(str)
    '''
    dict_trans = {}
    with open(trans_file, 'r') as f:
        for l in f:
            l = l.strip()
            line = l.split()
            utt = line.pop(0)
            dict_trans[utt] = line
    return dict_trans

def merge_frame_llhs(frame_llhs, states, nstates_per_phone, dict_state_to_phone):
    '''Merge per frame log-likelihood into per phoneme log-likelihood
    Args:
        frame_llhs(torch.tensor(float)): per frame llhs
        states: list of state ids(int) for best path
        dict_state_to_phone: state_id(int) -> phoneme(str)
    '''
    if (len(frame_llhs) != len(states)):
        sys.exit('Best path length does not match with likelihood !')
    phone_llhs = []
    ending = [i + nstates_per_phone - 1 for i in
        dict_state_to_phone.keys() if i % nstates_per_phone == 0]
    llh_sum = 0.
    frame_count = 0
    for i in range(len(states) - 1):
        llh_sum += frame_llhs[i]
        frame_count += 1
        if (states[i] != states[i+1]) and (states[i]) in ending:
            phone_llhs.append(llh_sum / frame_count)
            llh_sum = 0.
            frame_count = 0
    phone_llhs.append((llh_sum + frame_llhs[-1]) / (frame_count + 1))
    return torch.tensor(phone_llhs)

def smooth_llh(hyp_frame_llhs, ali_best_path, nstates_per_phone,
               dict_state_to_phone):
    '''Smooth hypothesis per frame log-likelihood with given align llhs
    Args:
    hyp_frame_llhs: torch.tensor([float])
    ali_best_path: list(int)
    nstates_per_phone: int
    dict_state_to_phone: statd_id(int) -> phoneme(str)
    Return:
    hyp_phone_llhs: torch.tensor([float])
    '''
    if (len(hyp_frame_llhs) != len(ali_best_path)):
        sys.exit('Hypothesis llhs not same length as alignment llhs !')
    phone_llhs = []
    ending = [i + nstates_per_phone - 1 for i in
    dict_state_to_phone.keys() if i % nstates_per_phone == 0]
    llh_sum = 0.
    frame_count = 0
    for i in range(len(ali_best_path) - 1):
        llh_sum += hyp_frame_llhs[i]
        frame_count += 1
        if (ali_best_path[i] != ali_best_path[i+1]) and (ali_best_path[i]) in ending:
            phone_llhs.append(llh_sum / frame_count)
            llh_sum = 0.
            frame_count = 0
    phone_llhs.append((llh_sum + hyp_frame_llhs[-1]) / (frame_count + 1))
    return torch.tensor(phone_llhs)
