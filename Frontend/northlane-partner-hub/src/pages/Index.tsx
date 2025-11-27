import { AnimatedBlocks } from '@/components/AnimatedBlocks';
import { HardwareRecommendation } from '@/components/HardwareRecommendation';
import { useState, useEffect } from 'react';

const Index = () => {
  const [isPageLoaded, setIsPageLoaded] = useState(false);

  useEffect(() => {
    setTimeout(() => setIsPageLoaded(true), 100);
  }, []);

  return (
    <div className="min-h-screen bg-background relative overflow-hidden">
      <AnimatedBlocks />
      
      <nav 
        className="relative z-10 px-6 py-6 flex justify-between items-center transition-all duration-700"
        style={{
          opacity: isPageLoaded ? 1 : 0,
          transform: isPageLoaded ? 'translateY(0)' : 'translateY(-20px)',
        }}
      >
        <div className="text-2xl font-bold">HardwareAI</div>
        <div className="flex gap-8 items-center">
          <a href="#how-it-works" className="hover:text-accent transition-colors">
            How it Works
          </a>
          <a href="#about" className="hover:text-accent transition-colors">
            About
          </a>
          <button className="px-6 py-2 bg-accent text-accent-foreground rounded-md hover:opacity-90 transition-opacity font-medium">
            Get Started
          </button>
        </div>
      </nav>

      <main className="relative z-10 container mx-auto px-6 pt-20 pb-32">
        <section 
          className="max-w-6xl mx-auto text-left mb-32 transition-all duration-1000"
          style={{
            opacity: isPageLoaded ? 1 : 0,
            transform: isPageLoaded ? 'translateY(0)' : 'translateY(30px)',
            transitionDelay: '0.2s',
          }}
        >
          <h1 className="text-6xl md:text-8xl font-bold mb-8 leading-tight">
            Hardware. Chosen.
            <br />
            Perfectly.
          </h1>
          <p className="text-xl md:text-2xl text-muted-foreground max-w-xl mb-12">
            AI-powered hardware recommendations
            <br />
            tailored to your exact needs and
            <br />
            budget.
          </p>
          <a href="#recommend" className="inline-block">
            <button className="px-8 py-4 border-2 border-foreground rounded-md text-lg hover:bg-accent hover:border-accent transition-all font-medium">
              Find Your Setup →
            </button>
          </a>
        </section>

        <div id="recommend">
          <HardwareRecommendation />
        </div>
      </main>
    </div>
  );
};

export default Index;
