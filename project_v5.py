from cmu_graphics import *
import numpy as np
import sounddevice as sd 
import random
import copy
    #imports below are from AI
import threading    #lets Muse server run in background

from pythonosc.dispatcher import Dispatcher 
    #dispatcher tells u what handler (alpha, beta, etc) to call
    #similar to how runApp auto calls onAppStart, redrawAll, onStep
from pythonosc.osc_server import BlockingOSCUDPServer

###################################################################################
##################    GENERAL APP STUFF    ########################################
###################################################################################

def onAppStart(app):
    runMusicVariables(app)
    runEEGVariables(app)
    runVisualVariables(app)
    app.steps = 0

def onStep(app):
    app.steps += 1
    updateEmotions(app)
    updateParticles(app)
    updateSoundProperties(app)
    app.arousalHistory.append(app.arousal)
    app.valenceHistory.append(app.valence)
    # keep list from getting too long
    if len(app.arousalHistory) > app.maxPoints:
        app.arousalHistory.pop(0)
        app.valenceHistory.pop(0)

###################################################################################
##################    EEG CODE    #################################################
###################################################################################

def runEEGVariables(app):
    app.valence = 0
    app.arousal = 0
    app.museThread = threading.Thread(target=startMuseServer, daemon=True)
    app.museThread.start()
    app.arousalHistory = []
    app.valenceHistory = []

#from AI
latest = {
    'alpha': None,
    'beta': None,
    'hsi': None
} #where livestream stores data

#all from AI; automatically called and stores new alpha/beta calues
def alpha_handler(address, *args):
    latest['alpha'] = args

def beta_handler(address, *args):
    latest['beta'] = args

def hsi_handler(address, *args):
    latest['hsi'] = args        

def all_handler(address, *args):
    pass
    #print("RECEIVED:", address, args)

#from AI. start server 
def startMuseServer():
    dispatcher = Dispatcher()
    dispatcher.map("/muse/elements/alpha_absolute", alpha_handler)
    dispatcher.map("/muse/elements/beta_absolute", beta_handler)
    dispatcher.map("/muse/elements/horseshoe", hsi_handler)
    dispatcher.set_default_handler(all_handler)  # optional, for debugging prints

    server = BlockingOSCUDPServer(("0.0.0.0", 5000), dispatcher)
    print("Listening on port 5000...")
    server.serve_forever()


#from AI; turn eeg data --> valence and arousal
def getMuseEmotion():
    if latest['alpha'] is None or latest['beta'] is None:
        return None

    alpha = latest['alpha']
    beta = latest['beta']
    #print("alpha:", latest['alpha'])
    #print("beta:", latest['beta'])  
    if len(alpha) < 4 or len(beta) < 4: 
        #basically if ur getting less than 4 arguments,
        #return None and skip getting the emotion for now. 
        #(in updateEmotions, if it's None, nothing changes; val/arousal same.)
        return None

    AF7 = 1
    AF8 = 2

    alphaAF7 = alpha[AF7]
    alphaAF8 = alpha[AF8]
    betaAF7 = beta[AF7]
    betaAF8 = beta[AF8]

    # AROUSAL (standard)
    alphaAvg = (alphaAF7 + alphaAF8) / 2
    betaAvg = (betaAF7 + betaAF8) / 2
    arousalRaw = betaAvg / (alphaAvg + 0.001)
    arousal = max(0, min(1, (arousalRaw - 0.9) / 0.8))
    #arousal = arousal*2 - 1

    # VALENCE (real method)
    valenceRaw = alphaAF8 - alphaAF7

    # scale it (IMPORTANT — raw values are big)
    valence = max(-1, min(1, valenceRaw * 0.75))

    return valence, arousal

def updateEmotions(app):
    museEmotion = getMuseEmotion()

    if museEmotion is not None:
        newValence, newArousal = museEmotion
        app.valence = 0.9 * app.valence + 0.1 * newValence #smoothing
        app.arousal = 0.7 * app.arousal + 0.3 * newArousal


###################################################################################
##################    MUSIC CODE    ###############################################
###################################################################################
def runMusicVariables(app):
    app.frequency = random.uniform(100,1000)
    app.amplitude = 0.6
    app.duration = 1

    app.phase = 0.0
    app.sampleRate = 44100
    #app.stream = None
    app.mySound = sine_tone(app, app.frequency, 1, app.amplitude)
    app.mySound2 = sine_tone(app, app.frequency, 1, app.amplitude)



#from Youtube Video
def sine_tone(app,
        frequency: int = 200,
        duration: float = 1.0,
        amplitude: float = 0.5,
        sample_rate: int=44100
        ) -> np.ndarray:
    n_samples = int(sample_rate * duration)
    time_points = np.linspace(0, duration, n_samples, False)
    #make sine wave. .sin() takes in angle in radians.
    #frequency in hz --> radians per second (angular freq), using 2pi * frequency
    #then, we get angular position, or phase of the wave for each time pt
    sine = np.sin(2*np.pi*frequency * time_points)
    sine *= amplitude
    return sine

#from Youtube video
def apply_envelope(app, sound: np.array, adsr: list, sample_rate: int = 44100) -> np.array:
    sound = sound.copy()
    #to get number of samples, multiply duration by sample rate
    attack_samples = int(adsr[0] * sample_rate)
    decay_samples = int(adsr[1] * sample_rate)
    release_samples = int(adsr[3] * sample_rate)
    sustain_samples = len(sound) - (attack_samples +decay_samples + release_samples)

    #ATTACK phase:
    sound[:attack_samples] *= np.linspace(0,1,attack_samples)
    #DECAY phase:
    sound[attack_samples:attack_samples + decay_samples] *= np.linspace(1,adsr[2],decay_samples)
    #SUSTAIN phase:
    sound[attack_samples + decay_samples:attack_samples + decay_samples + sustain_samples] *= adsr[2]
    #RELEASE phase:
    sound[attack_samples + decay_samples + sustain_samples:] *= np.linspace(adsr[2], 0, release_samples)
    return sound

def updateSoundProperties(app):
    return sadScale(app)
    if app.valence > 0 and app.arousal < 0.5:
        return calmScale(app)
    elif app.valence > 0 and app.arousal > 0.5:
        return happyScale(app)
    elif app.valence < 0 and app.arousal < 0.5:
        return sadScale(app)
    else:
        return angryScale(app)
    
    

def angryScale(app):
    ePhrygianDominant = [164.8, 174.6, 207.7, 220, 247, 261.6, 293.7, 
                         329.6, 349.2, 415.3, 440, 493.9, 523.3, 387.3,
                         658.3]
    noteIndex = random.randint(2,9)
    app.frequency = ePhrygianDominant[noteIndex]
    amplitude = 1 #make it equal to app.arousal
    newDuration = random.choice([2, 1])
    #app.mySound = sine_tone(app, frequency = app.frequency, amplitude = amplitude, duration = newDuration)
    #noteIndex2 = random.randint(6,12)
    #freq2 = pentatonicScale[noteIndex2]
    #app.mySound2 = sine_tone(app, frequency = freq2, duration = newDuration)
    attack = 0.01
    decay = 0.05
    sustain = 0.5
    release = 0.01
    totalADSR = attack + decay + sustain + release
    app.duration = newDuration

    random1 = random.randint(0,3)
    random2 = random.randint(4,10)
    sines = [sine_tone(app, frequency = ePhrygianDominant[i], amplitude = 0.7/(1+i), duration = app.duration) for i in range(random1, random2)]

    app.mySound = sum(sines)
    app.mySound = apply_envelope(app, app.mySound, [attack, decay, sustain, release]) 

    if app.steps % (app.stepsPerSecond * app.duration) == 0:
        sd.play(app.mySound)

    
def calmScale(app):
    pentatonicScale = [110, 130.8, 146.83, 164.81, 196, 
                       220, 261.6, 293.7, 329.6, 392,
                       440, 523.3, 587.3, 629.3, 784]
    
    noteIndex1 = random.randint(2, 6)
    app.frequency = pentatonicScale[noteIndex1]
    #amplitude = app.arousal + 20
    durations = [0.25, 0.5, 0.75, 1]
    durationIndex = random.randint(0, 3)
    newDuration = durations[durationIndex]

    app.mySound = sine_tone(app, frequency = app.frequency, duration = newDuration)
    #noteIndex2 = random.randint(6,12)
    #freq2 = pentatonicScale[noteIndex2]
    #app.mySound2 = sine_tone(app, frequency = freq2, duration = newDuration)
    attack = 0.2
    decay = 0.3
    sustain = 0.6
    release = 0.2
    totalADSR = attack + decay + sustain + release
    
    app.duration = min(totalADSR, newDuration)
    

    random1 = random.randint(2,6) 
    random2 = random1 + 2 #third
    random3 = random1 + 5 #sixth
    sines = [sine_tone(app, frequency = pentatonicScale[i], amplitude = 0.7/(1+i), duration = app.duration) for i in range(random1, random3)]

    #app.mySound = sum(sines)
    app.mySound = apply_envelope(app, app.mySound, [0.1, 0.05, 0.4, 0.1]) #attack, decay, sustain, release

    if app.steps % (app.stepsPerSecond * app.duration) == 0:
        sd.play(app.mySound)

def sadScale(app):
    aHarmonicMinor = [220, 247, 261.6, 293.7, 329.7, 349.2, 415.3,
                      440, 493.9, 523.3, 587.3, 659.3, 698.5, 830.61]
    noteIndex1 = random.randint(2, 6)
    app.frequency = aHarmonicMinor[noteIndex1]
    #amplitude = app.arousal + 20
    durations = [0.25, 0.5, 0.75, 1]
    durationIndex = random.randint(0, 3)
    newDuration = durations[durationIndex]

    app.mySound = sine_tone(app, frequency = app.frequency, amplitude = 0.3, duration = newDuration)
    noteIndex2 = random.randint(6,7)
    freq2 = aHarmonicMinor[noteIndex2]
    app.mySound2 = sine_tone(app, frequency = freq2, amplitude = 0.3, duration = newDuration)

    attack = 0.5
    decay = 0.3
    sustain = 0.6
    release = 0.5
    totalADSR = attack + decay + sustain + release
    
    app.duration = min(totalADSR, newDuration)

    random1 = random.randint(2,6) 
    random2 = random1 + 2 #third
    random3 = random1 + 5 #sixth
   
    sines = [sine_tone(app, frequency = aHarmonicMinor[i], amplitude = 0.7/(1+i), duration = app.duration) for i in range(random1, random3)]
    #app.mySound = sum(sines)
    #app.mySound = apply_envelope(app, app.mySound, [0.2, 0.05, 0.9, 0.2]) #attack, decay, sustain, release

    if app.steps % (app.stepsPerSecond * app.duration) == 0:
        sd.play(app.mySound + app.mySound2, 44100)

def happyScale(app):
    cWholeTone = [261.6, 329.7, 329.6, 370, 415.3, 466.2, 
                  523.3, 587.3, 659.3, 740, 830.6, 932.3] 
    
    #maybe not whole tone

    noteIndex1 = random.randint(2, 6)
    app.frequency = cWholeTone[noteIndex1]
    #amplitude = app.arousal + 20
    newDuration = random.choice([0.1, 0.2, 0.3])
    app.mySound = sine_tone(app, frequency = app.frequency, duration = newDuration)
    #noteIndex2 = random.randint(6,12)
    #freq2 = pentatonicScale[noteIndex2]
    #app.mySound2 = sine_tone(app, frequency = freq2, duration = newDuration)
    attack = 0.01
    decay = 0.05
    sustain = 0.5
    release = 0.01
    totalADSR = attack + decay + sustain + release
    
    app.duration = min(totalADSR, newDuration)
    

    random1 = random.randint(2,6) 
    random2 = random1 + 2 #third
    random3 = random1 + 5 #sixth
    if app.steps % app.stepsPerSecond == 0:
        print(cWholeTone[random1], cWholeTone[random2])
    sines = [sine_tone(app, frequency = cWholeTone[i], amplitude = 0.7/(1+i), duration = 2) for i in range(random1, random3)]

    #app.mySound = sum(sines)
    app.mySound = apply_envelope(app, app.mySound, [attack, decay, sustain, release]) 

    if app.steps % (app.stepsPerSecond * app.duration) == 0:
        sd.play(app.mySound)




 




###################################################################################
##################    VISUAL CODE    ##############################################
###################################################################################

def runVisualVariables(app):
    app.particles = []
    for _ in range(80):
        app.particles.append(makeParticle(app))#make particle into OOP; particle object
    
    app.maxPoints = 200   # how many points to keep on screen

#from AI     
def getColorFromValence(valence):
    valence = max(-1, min(1, valence * 6)) #scale it more
    t = (valence + 1) / 2 # map [-1,1] → [0,1]
    r = 255
    g = int(255 * t)
    b = 0
    return rgb(r, g, b)

def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='black')
    status = "LIVE" if latest['alpha'] is not None else "WAITING"
    drawLabel(status, 60, 20, fill='white')
    
    for p in app.particles:
        color = getColorFromValence(app.valence)
        drawCircle(p['x'], p['y'], p['r'], fill=color, opacity=60)
    
    drawLabel(f'Valence: {app.valence:.2f}', app.width-80, 20, fill='white', align = 'left')
    drawLabel(f'Arousal: {app.arousal:.2f}', app.width-80, 40, fill='white', align = 'left')
    drawGraphs(app)

def drawGraphs(app):
    # graph settings
    graphWidth = 300
    graphHeight = 100
    margin = 20

    # positions
    x0 = margin
    y0 = app.height - graphHeight - margin

    # draw background
    drawRect(x0, y0, graphWidth, graphHeight, fill=None, border='white')
    drawRect(x0 + 340, y0, graphWidth, graphHeight, fill=None, border='white')

    # labels
    drawLabel("Arousal", x0 + 40, y0 - 10, fill='white')
    drawLabel("Valence", x0 + 360, y0 - 10, fill='white')

    # spacing between points
    if len(app.arousalHistory) > 1:
        dx = graphWidth / len(app.arousalHistory)

        # draw arousal (left graph)
        for i in range(len(app.arousalHistory) - 1):
            x1 = x0 + i * dx
            x2 = x0 + (i + 1) * dx

            y1 = y0 + graphHeight * (1 - app.arousalHistory[i])
            y2 = y0 + graphHeight * (1 - app.arousalHistory[i + 1])

            drawLine(x1, y1, x2, y2, fill='cyan')

        # draw valence (right graph, shifted right)
        offset = graphWidth + 40

        for i in range(len(app.valenceHistory) - 1):
            x1 = x0 + offset + i * dx
            x2 = x0 + offset + (i + 1) * dx

            # valence is [-1,1] → map to [0,1]
            v1 = (app.valenceHistory[i] + 1) / 2
            v2 = (app.valenceHistory[i + 1] + 1) / 2

            y1 = y0 + graphHeight * (1 - v1)
            y2 = y0 + graphHeight * (1 - v2)

            drawLine(x1, y1, x2, y2, fill='yellow')

def makeParticle(app):
    return {
        'x': random.uniform(0, app.width),
        'y': random.uniform(0, app.height),
        'dx': random.uniform(-2, 2),
        'dy': random.uniform(-2, 2),
        'r': random.uniform(2, 6)
        }

def updateParticles(app):
    jitter = .5 + 6*app.arousal #jitter is linked to arousal
    drift = 1.5 * app.valence #direction it moves
    for p in app.particles:
        p['x'] += p['dx'] + random.uniform(-jitter, jitter)
        p['y'] += p['dy'] + random.uniform(-jitter, jitter) - drift #drift alr linked to valence, up/down

        if p['x'] < 0: p['x'] = app.width
        if p['x'] > app.width: p['x'] = 0
        if p['y'] < 0: p['y'] = app.height
        if p['y'] > app.height: p['y'] = 0




def main():
    runApp()
    


main()