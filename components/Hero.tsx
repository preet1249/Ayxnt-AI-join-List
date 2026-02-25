import React, { useState, useEffect } from "react";
import { Check } from "lucide-react";

const Hero = () => {
  const [timeLeft, setTimeLeft] = useState({
    days: 50,
    hours: 0,
    minutes: 0,
    seconds: 0,
  });
  const [isSubmitted, setIsSubmitted] = useState(false);

  useEffect(() => {
    // Set target date to 50 days from now
    const targetDate = new Date();
    targetDate.setDate(targetDate.getDate() + 50);

    const interval = setInterval(() => {
      const now = new Date();
      const difference = targetDate.getTime() - now.getTime();

      if (difference <= 0) {
        clearInterval(interval);
        setTimeLeft({ days: 0, hours: 0, minutes: 0, seconds: 0 });
      } else {
        const days = Math.floor(difference / (1000 * 60 * 60 * 24));
        const hours = Math.floor((difference % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((difference % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((difference % (1000 * 60)) / 1000);

        setTimeLeft({ days, hours, minutes, seconds });
      }
    }, 1000);

    return () => clearInterval(interval);
  }, []);

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault();
    setIsSubmitted(true);
  };

  return (
    <section className="relative h-screen w-full overflow-hidden text-white bg-[#0a0a0a]">
      {/* Background Image Layer */}
      <div 
        className="absolute inset-0 z-0 bg-cover bg-center"
        style={{
          backgroundImage: "url('https://image2url.com/r2/default/images/1770291091051-6403729f-f42e-40cb-b730-a7a466479fad.jpg')"
        }}
      />
      
      {/* Overlay Layer - Black square with 18% opacity */}
      <div className="absolute inset-0 z-1 bg-black/18 pointer-events-none" />

      {/* Logo - Top Center */}
      <div className="absolute -top-5 left-1/2 -translate-x-1/2 z-20">
        <img 
          src="https://image2url.com/r2/default/images/1772038298617-95e839cb-8bc3-4709-8488-9fe335936b36.png" 
          alt="Logo" 
          className="h-28 w-auto object-contain"
        />
      </div>

      {/* Hero Content */}
      <div className="relative z-10 h-full flex flex-col items-center justify-center text-center px-4">
        {!isSubmitted ? (
          <>
            <h1 className="font-inter font-extralight text-[64px] tracking-tighter leading-[1.1] mb-6">
              Join the Waitlist
            </h1>
            
            <p className="font-inter font-light text-lg text-white/80 mb-10 tracking-tight max-w-lg">
              Be the first to experience the future of intelligent applications.
            </p>

            <form className="flex flex-col sm:flex-row gap-3 w-full max-w-[480px]" onSubmit={handleSubmit}>
              <input 
                type="email" 
                placeholder="Enter your email address" 
                className="flex-1 px-6 py-3.5 bg-[#111111]/45 backdrop-blur-sm border border-white/10 rounded-full text-white placeholder-white/40 font-inter font-light text-sm focus:outline-none focus:border-white/30 transition-all"
                required
              />
              <button 
                type="submit" 
                className="px-8 py-3.5 bg-white text-black font-inter font-medium text-sm rounded-full hover:bg-gray-100 transition-colors cursor-pointer whitespace-nowrap"
              >
                Join Now
              </button>
            </form>
          </>
        ) : (
          <div className="flex flex-col items-center animate-in fade-in zoom-in duration-500">
            <div className="w-20 h-20 bg-green-500/20 rounded-full flex items-center justify-center mb-6 backdrop-blur-sm border border-green-500/30 shadow-[0_0_30px_rgba(34,197,94,0.2)]">
              <Check className="w-10 h-10 text-green-400" strokeWidth={1.5} />
            </div>
            <h3 className="text-4xl font-inter font-light text-white mb-3 tracking-tight">Thank You!</h3>
            <p className="text-white/70 font-inter font-light text-lg tracking-wide">You've been added to the waitlist.</p>
          </div>
        )}

        {/* Countdown Timer */}
        <div className={`mt-16 flex items-center gap-8 sm:gap-12 font-afacad text-white/90 ${isSubmitted ? 'absolute bottom-20' : ''}`}>
          <div className="flex flex-col items-center gap-1">
            <span className="text-4xl font-light tracking-tight">{String(timeLeft.days).padStart(2, '0')}</span>
            <span className="text-[10px] uppercase tracking-[0.2em] opacity-60">Days</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="text-4xl font-light tracking-tight">{String(timeLeft.hours).padStart(2, '0')}</span>
            <span className="text-[10px] uppercase tracking-[0.2em] opacity-60">Hours</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="text-4xl font-light tracking-tight">{String(timeLeft.minutes).padStart(2, '0')}</span>
            <span className="text-[10px] uppercase tracking-[0.2em] opacity-60">Minutes</span>
          </div>
          <div className="flex flex-col items-center gap-1">
            <span className="text-4xl font-light tracking-tight">{String(timeLeft.seconds).padStart(2, '0')}</span>
            <span className="text-[10px] uppercase tracking-[0.2em] opacity-60">Seconds</span>
          </div>
        </div>
      </div>
    </section>
  );
};

export default Hero;