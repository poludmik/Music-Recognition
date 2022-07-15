import math, random
import os
import torch
import pandas as pd
import numpy as np
import torchaudio
from torchaudio import transforms
import IPython.display as ipd
import matplotlib.pyplot as plt
from pydub import AudioSegment
from pydub.utils import make_chunks


class SoundTools:

    @staticmethod
    def open(sound_file):
        signal, sample_rate = torchaudio.load(sound_file)
        return signal, sample_rate

    @staticmethod
    def rechannel(sound, new_num_channels):
        (signal, sample_rate) = sound
        if signal.shape[0] == new_num_channels:
            return sound
        if new_num_channels == 1:
            return signal[0], sample_rate
        if new_num_channels == 2:
            return torch.cat((signal, signal)), sample_rate

    @staticmethod
    def resample(sound, new_sample_rate):
        signal, sample_rate = sound
        if sample_rate == new_sample_rate:
            return sound

        transform = transforms.Resample(sample_rate, new_sample_rate)
        signal = transform(signal)
        if signal.size(dim=0) == 2:
            return torch.cat((signal, signal)), new_sample_rate
        return signal, new_sample_rate

    @staticmethod
    def sec_to_sn(t_sec, sr):
        return math.floor(t_sec * sr)

    @staticmethod
    def sn_to_sec(sn, sr):
        return math.ceil((sn / sr))

    @staticmethod
    def cut_or_pad(sound, t_sec):
        signal, sample_rate = sound
        samples_number = SoundTools.sec_to_sn(t_sec, sample_rate)

        if signal.size(dim=1) == samples_number:
            return sound
        elif signal.size(dim=1) > samples_number:
            signal = signal[:, :samples_number]
        elif signal.size(dim=1) < samples_number:
            difference = samples_number - signal.size(dim=1)
            channels = signal.size(dim=0)
            if difference % 2 == 0:
                pad_start = torch.zeros((channels, difference // 2))
                pad_end = pad_start
            else:
                pad_start = torch.zeros((channels, difference // 2))
                pad_end = torch.zeros((channels, difference - difference // 2))
            signal = torch.cat((pad_start, signal, pad_end), dim=1)

        return signal, sample_rate

    @staticmethod
    def plot_sound(sound):
        sig, sr = sound
        time_in_s = SoundTools.sn_to_sec(sig.size(dim=1), sr)
        t = np.linspace(0, time_in_s, sr * time_in_s, endpoint=False)
        plt.plot(t, sig[0].numpy()[0:sr * time_in_s])
        plt.show()

    @staticmethod
    def random_shift(sound, max_seconds):
        sig, sr = sound
        seconds_to_shift = random.uniform(-max_seconds, max_seconds)
        sample_num_to_shift = SoundTools.sec_to_sn(seconds_to_shift, sr)
        sig = torch.roll(sig, sample_num_to_shift, 1)
        return sig, sr

    @staticmethod
    def spectrogram(sound, n_mels=90, n_fft=510, hop_len=None):
        sig, sr = sound
        max_db = 80
        spectrum = transforms.MelSpectrogram(sample_rate=sr, n_fft=n_fft, hop_length=hop_len, n_mels=n_mels)(sig)
        return transforms.AmplitudeToDB(top_db=max_db)(spectrum)

    @staticmethod
    def plot_spectogram(spectogram):
        # will plot one channel spectogram
        spectr = spectogram[0, :, :]
        plt.imshow(spectr)
        plt.show()

    @staticmethod
    def shadow_spectr_segment(spectrogram):
        # For data augmentation
        shadow_value = spectrogram.mean()
        max_time_percent = 0.05
        max_freq_percent = 0.1
        spectrogram = transforms.TimeMasking(max_time_percent * spectrogram.size(dim=2))(spectrogram, shadow_value)
        spectrogram = transforms.FrequencyMasking(max_freq_percent * spectrogram.size(dim=1))(spectrogram, shadow_value)
        return spectrogram
