
import numpy as np
import sounddevice as sd 

def main():
    mysound1 = white_noise()
    mysound2 = sine_tone()    
    #harmonic overtones = frequencies that are multiples of the fundamental
    #additive synthesis = combining sine waves
    #wave superposition: idea that when 2+ waves overlapping --> their amplitudes combine
    sine1 = sine_tone(200, 1, 0.6)
    sine2 = sine_tone(400, 1, 0.3)
    sine3 = sine_tone(800, 1, 0.2)
    mysound3 = sum([sine1, sine2, sine3])

    #for more complex additive synthesis, use for loop:
    sines = [sine_tone(frequency = 200*i, amplitude = 0.7/i) for i in range(1,31,2)]
    mysound4 = sum(sines)

    #beating effects happens when close frequencies interact
    sinesBeating = [sine_tone(200, 1, 0.6), sine_tone(205, 1, 0.6)]
    mysound5 = sum(sinesBeating)
    
    sd.play(mysound5)
    sd.wait() #wait til audio plays before executing more code

def sine_tone(
        frequency: int = 440,
        duration: float = 1.0,
        amplitude: float = 0.5,
        sample_rate: int=44100
        ) -> np.ndarray:
    n_samples = int(sample_rate * duration)
    
    #make sequence of time pts. generate array of evenly spaced vals
    #range is 0 to duration, length is n samples,false means endpoint excluded
    time_points = np.linspace(0, duration, n_samples, False)
    
    #make sine wave. .sin() takes in angle in radians.
    #frequency in hz --> radians per second (angular freq), using 2pi * frequency
    #then, we get angular position, or phase of the wave for each time pt
    sine = np.sin(2*np.pi*frequency * time_points)
    sine *= amplitude
    return sine


def white_noise(
        duration: float = 1.0,
        amplitude: float = 0.5,
        sample_rate: int=44100
        ) -> np.ndarray:#returns numpy array
    #total number of samples needed:
    n_samples = int(sample_rate * duration)
    #whtie noise with values from -1 to 1 and n samples
    noise = np.random.uniform(-1, 1, n_samples)
    noise *= amplitude #scale it by amplitude
    return noise

main()

# Next video
# ADSR envelope: attack, decay, sustain, release
# attack = silence to sound
# decay = time it takes to decrease from peak amplitude to sustained
# sustain = defined as amplitude, not time
# release = sustain level to silence (can be gradual or abrupt)
#     for example, piano has short release; violin has long
