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
    for p in app.particles:
        p.updateParticle(app)
    updateScale(app)
    app.mySound.play(app)


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
    app.mySound = sine_tone(app, app.frequency, 1, app.amplitude) #default vals to start
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

def updateScale(app):
    app.mySound = HappyScale(app)
    
    # if app.valence > 0 and app.arousal < 0.5:
    #     app.mySound = CalmScale(app)
    # elif app.valence > 0 and app.arousal > 0.5:
    #     return happyScale(app)
    # elif app.valence < 0 and app.arousal < 0.5:
    #     app.mySound = SadScale(app)
    # else:
    #     app.mySound = AngryScale(app)
    
    
class Scale:
    def __init__(self, app):
        self.notes = []
        self.attack = 0.1 #default ADSR values
        self.decay = 0.05
        self.sustain = 0.5
        self.release = 0.1 
        self.duration = app.duration
        #total duration = 0.25
        
    def play(self, app):
        pass #diff for each subclass depending on number of notes

class AngryScale(Scale):
    def __init__(self, app):
        super().__init__(app)
        self.notes =    [164.8, 174.6, 207.7, 220, 247, 261.6, 293.7, 
                        329.6, 349.2, 415.3, 440, 493.9, 523.3, 387.3,
                        658.3]
        self.attack = 0.01
        self.release = 0.01
        self.duration = self.attack + self.decay + self.release
        
    def updateScaleNotes(self, app):
        index1 = random.randint(0, 3)
        index2 = random.randint(4,10) # dont hardcode it?
        self.duration = random.choice([2, 1])
        app.duration = self.duration #maybe exclude

        sines = [sine_tone(app, frequency = self.notes[i], amplitude = 0.7/(1+i), duration = self.duration) for i in range(index1, index2)]
        app.mySound = sum(sines)
        app.mySound = apply_envelope(app, app.mySound, [self.attack, self.decay, self.sustain, self.release]) 

    def play(self, app):
        if app.steps % (app.stepsPerSecond * self.duration) == 0:
            self.updateScaleNotes(app)
            sd.play(app.mySound)

class CalmScale(Scale):
    def __init__(self, app):
        super().__init__(app)
        self.notes =    [110, 130.8, 146.83, 164.81, 196, 
                        220, 261.6, 293.7, 329.6, 392,
                        440, 523.3, 587.3, 629.3, 784]
        self.attack = 0.1
        self.decay = 0.05
        self.sustain = 0.4
        self.release = 0.1
        self.duration = self.attack + self.decay + self.release
        #total ADSR = 0.25

    def updateScaleNotes(self, app): 
        durations = [0.25, 0.5, 0.75, 1]
        durationIndex = random.randint(0, 3)
        self.duration = durations[durationIndex]
        app.duration = self.duration #maybe not needed

        index1 = random.randint(2, 6)
        frequency1 = self.notes[index1]
        #amplitude = app.arousal + 20
        app.mySound = sine_tone(app, frequency = frequency1, duration = self.duration)
        app.mySound = apply_envelope(app, app.mySound, [self.attack, self.decay, self.sustain, self.release])

        index2 = random.randint(7,10)
        frequency2 = self.notes[index2]
        app.mySound2 = sine_tone(app, frequency = frequency2, duration = self.duration)
        app.mySound2 = apply_envelope(app, app.mySound, [self.attack, self.decay, self.sustain, self.release])

    def play(self, app):
        if app.steps % (app.stepsPerSecond * app.duration) == 0:
            self.updateScaleNotes(app)
            sd.play(app.mySound + app.mySound2, 44100)

class SadScale(Scale):
    def __init__(self, app):
        super().__init__(app)
        self.notes =    [220, 247, 261.6, 293.7, 329.7, 349.2, 415.3,
                      440, 493.9, 523.3, 587.3, 659.3, 698.5, 830.61]
        self.attack = 0.3
        self.decay = 0.3
        self.sustain = 0.6
        self.release = 0.3
        self.duration = self.attack + self.decay + self.release
        #total ADSR = 0.9

    def updateScaleNotes(self, app):
        durations = [1, 1.5, 2, 2.5]
        durationIndex = random.randint(0, 3)
        self.duration = durations[durationIndex]
        app.duration = self.duration #maybe not needed

        index1 = random.randint(2, 6)
        frequency1 = self.notes[index1]
        #amplitude = app.arousal + 20
        app.mySound = sine_tone(app, frequency = frequency1, amplitude = 0.3, duration = self.duration)
        app.mySound = apply_envelope(app, app.mySound, [self.attack, self.decay, self.sustain, self.release])

        index2 = random.randint(7,10)
        frequency2 = self.notes[index2]
        app.mySound2 = sine_tone(app, frequency = frequency2, amplitude = 0.3, duration = self.duration)
        app.mySound2 = apply_envelope(app, app.mySound, [self.attack, self.decay, self.sustain, self.release])
        
    def play(self, app):
        if app.steps % (app.stepsPerSecond * app.duration) == 0:
            self.updateScaleNotes(app)
            sd.play(app.mySound + app.mySound2, 44100)

class HappyScale(Scale):
    def __init__(self, app):
        super().__init__(app)
        self.notes =    [261.6, 329.7, 329.6, 370, 415.3, 466.2, 
                        523.3, 587.3, 659.3, 740, 830.6, 932.3] 
        self.attack = 0.01
        self.release = 0.01
        self.duration = self.attack + self.decay + self.release # = 0.07
        
    def updateScaleNotes(self, app):
        index1 = random.randint(2, 6)
        index2 = index1 + 1 # + 5 gives sixth. for third, do +2.
        self.duration = random.choice([0.1, 0.2, 0.3])
        app.duration = self.duration #maybe exclude

        # noteIndex1 = random.randint(2, 6)
        # frequency1 = self.notes[noteIndex1]
        # app.mySound = sine_tone(app, frequency = frequency1, duration = self.duration)

        # noteIndex2 = random.randint(7, 12)
        # frequency2 = self.notes[noteIndex2]
        # app.mySound = sine_tone(app, frequency = frequency2, duration = self.duration)

        sines = [sine_tone(app, frequency = self.notes[i], amplitude = 0.7/(1+i), duration = self.duration) for i in range(index1, index2)]
        app.mySound = sum(sines)
        app.mySound = apply_envelope(app, app.mySound, [self.attack, self.decay, self.sustain, self.release]) 

    def play(self, app):
        if app.steps % (app.stepsPerSecond * self.duration) == 0:
            self.updateScaleNotes(app)
            sd.play(app.mySound)
    def play(self, app):
        if app.steps % (app.stepsPerSecond * app.duration) == 0:
            self.updateScaleNotes(app)
            sd.play(app.mySound)





###################################################################################
##################    VISUAL CODE    ##############################################
###################################################################################

def runVisualVariables(app):
    app.particles = []
    for _ in range(80):
        p = Particle(app)
        app.particles.append(p)
    app.maxPoints = 200   # how many points to keep on screen

class Particle:
    def __init__(self, app):
        self.x = random.uniform(0, app.width)
        self.y = random.uniform(0, app.height)
        self.dx = random.uniform(-2, 2)
        self.dy = random.uniform(-2, 2)
        self.r = random.uniform(2, 6)
        self.color = None

    def getParticleColorFromValence(self, app, valence):
        valence = max(-1, min(1, valence * 6)) #scale it more
        t = (valence + 1) / 2 # map [-1,1] → [0,1]
        r = 255
        g = int(255 * t)
        b = 0
        return rgb(r, g, b)
        
    def updateParticle(self, app):
        self.color = self.getParticleColorFromValence(app, app.valence)
        jitter = 0.5 + 6 * app.arousal #jitter is linked to arousal
        drift = 1.5 * app.valence #direction it moves
        
        self.x += self.dx + random.uniform(-jitter, jitter)
        self.y += self.dy + random.uniform(-jitter, jitter) - drift #drift alr linked to valence, up/down

        if self.x < 0: self.x = app.width
        if self.x > app.width: self.x = 0
        if self.y < 0: self.y = app.height
        if self.y > app.height: self.y = 0

def redrawAll(app):
    drawRect(0, 0, app.width, app.height, fill='black')
    status = "LIVE" if latest['alpha'] is not None else "WAITING"
    drawLabel(status, 60, 20, fill='white')
    for particle in app.particles:
        drawCircle(particle.x, particle.y, particle.r, fill = particle.color, opacity=60)
    
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



def main():
    runApp()
    


main()