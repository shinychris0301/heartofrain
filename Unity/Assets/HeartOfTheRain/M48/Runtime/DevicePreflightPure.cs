using System;

namespace HeartOfTheRain.M48 {
    public enum GesturePhase { None, Began, Held, Ended, Canceled }
    public enum GestureDecision { None, Begin, Commit, Cancel }
    // One owning pointer per gesture. An interruption requires all contacts to lift.
    public sealed class BoardGestureGate {
        bool armed,suppressed,touch;int owner;
        public void Interrupt(){armed=false;suppressed=true;}
        public void Reset(){armed=false;suppressed=false;}
        public GestureDecision Advance(int contacts,int id,bool isTouch,GesturePhase phase,bool allowed){
            if(!allowed){Interrupt();return GestureDecision.Cancel;}
            if(contacts==0){bool wasArmed=armed;Reset();return wasArmed?GestureDecision.Cancel:GestureDecision.None;}
            if(contacts!=1||phase==GesturePhase.Canceled){Interrupt();return GestureDecision.Cancel;}
            if(suppressed)return GestureDecision.None;
            if(armed&&(id!=owner||isTouch!=touch)){Interrupt();return GestureDecision.Cancel;}
            if(phase==GesturePhase.Began){
                if(armed){Interrupt();return GestureDecision.Cancel;}
                armed=true;owner=id;touch=isTouch;return GestureDecision.Begin;
            }
            if(phase==GesturePhase.Ended){bool commit=armed;armed=false;return commit?GestureDecision.Commit:GestureDecision.None;}
            if(phase==GesturePhase.None&&armed){Interrupt();return GestureDecision.Cancel;}
            return GestureDecision.None;
        }
    }
    // Duration uses observed active frame intervals, rather than a frame-count timer.
    public sealed class ReviewMeasurementClock {
        public const double DefaultDurationSeconds=600;
        public const int MaximumSamples=120000;
        public double ActiveSeconds {get;private set;}
        public double RequestedSeconds {get;private set;}
        public int Samples {get;private set;}
        public int ExcludedIntervals {get;private set;}
        public string EndReason {get;private set;}="";
        bool skipBoundary;
        public void Begin(double requestedSeconds=DefaultDurationSeconds){
            if(double.IsNaN(requestedSeconds)||double.IsInfinity(requestedSeconds)||requestedSeconds<=0)throw new ArgumentOutOfRangeException(nameof(requestedSeconds));
            ActiveSeconds=0;Samples=0;ExcludedIntervals=0;EndReason="";RequestedSeconds=requestedSeconds;skipBoundary=true;
        }
        public void Interrupt(){skipBoundary=true;}
        public bool Observe(double seconds,bool eligible){
            if(RequestedSeconds<=0||EndReason!="")return false;
            if(!eligible){skipBoundary=true;ExcludedIntervals++;return false;}
            if(skipBoundary){skipBoundary=false;ExcludedIntervals++;return false;}
            if(double.IsNaN(seconds)||double.IsInfinity(seconds)||seconds<=0){ExcludedIntervals++;return false;}
            ActiveSeconds+=seconds;Samples++;
            if(ActiveSeconds+1e-7>=RequestedSeconds)EndReason="DURATION_REACHED";
            else if(Samples>=MaximumSamples)EndReason="SAMPLE_LIMIT";
            return true;
        }
    }
}
