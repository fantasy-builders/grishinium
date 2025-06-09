"use client";
import { Button } from "@/components/Button";
import { StarsImage } from "@/assets";
import { motion, useScroll, useTransform } from "framer-motion";
import { useRef } from "react";
import Image from "next/image";
import Link from "next/link";

export const Hero = () => {
  const sectionRef = useRef<HTMLElement>(null);
  const { scrollYProgress } = useScroll({
    target: sectionRef,
    offset: ["start end", "end start"],
  });

  const backgroundPositionY = useTransform(
    scrollYProgress,
    [0, 1],
    [-300, 300],
  );

  return (
    <motion.section
      ref={sectionRef}
      className="h-[492px] md:h-[800px] flex items-center overflow-hidden relative [mask-image:linear-gradient(to_bottom,transparent,black_10%,black_90%,transparent)]"
      style={{ backgroundImage: `url(${StarsImage.src})`, backgroundPositionY }}
      animate={{
        backgroundPositionX: StarsImage.width,
      }}
      transition={{
        repeat: Infinity,
        duration: 100,
        ease: "linear",
      }}
    >
      <div className="absolute inset-0 bg-[radial-gradient(75%_75%_at_center_center,rgb(140,69,255,0.5)_15%,rgb(14,0,36,0.5)_78%,transparent)]"></div>
      {/* Start Planet */}
      <div className="absolute size-64 md:size-96 bg-purple-500 border border-white/20 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 bg-[radial-gradient(50%_50%_at_16.8%_18.3%,white,rgb(184,148,255)_37.7%,rgb(24,0,66))] shadow-[-20px_-20px_50px_rgb(255,255,255,0.5),-20px_-20px_80px_rgb(255,255,255,0.1),0_0_50px_rgb(140,69,255)] rounded-full"></div>
      {/* End Planet */}
      {/* Start Ring 1 */}
      <motion.div
        style={{
          translateY: "-50%",
          translateX: "-50%",
        }}
        animate={{
          rotate: "1turn",
        }}
        transition={{
          repeat: Infinity,
          duration: 60,
          ease: "linear",
        }}
        className="absolute size-[344px] md:size-[580px] border border-white opacity-20 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
      >
        <div className="absolute size-2 bg-white top-1/2 left-0 -translate-x-1/2 -translate-y-1/2 rounded-full"></div>
        <div className="absolute size-2 bg-white top-0 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"></div>
        <div className="absolute size-5 border border-white top-1/2 left-full -translate-x-1/2 -translate-y-1/2 rounded-full inline-flex justify-center items-center">
          <div className="size-2 bg-white rounded-full"></div>
        </div>
      </motion.div>
      {/* End Ring 1 */}
      {/* Start Ring 2 */}
      <motion.div
        style={{
          translateY: "-50%",
          translateX: "-50%",
        }}
        animate={{
          rotate: "-1turn",
        }}
        transition={{
          repeat: Infinity,
          duration: 60,
          ease: "linear",
        }}
        className="absolute size-[444px] md:size-[780px] border border-dashed border-white/20 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
      ></motion.div>
      {/* End Ring 2 */}
      {/* Start Ring 3 */}
      <motion.div
        style={{
          translateY: "-50%",
          translateX: "-50%",
        }}
        animate={{
          rotate: "1turn",
        }}
        transition={{
          repeat: Infinity,
          duration: 90,
          ease: "linear",
        }}
        className="absolute size-[544px] md:size-[980px] border border-white opacity-20 top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 rounded-full"
      >
        <div className="absolute size-2 bg-white top-1/2 left-0 -translate-x-1/2 -translate-y-1/2 rounded-full"></div>
        <div className="absolute size-2 bg-white top-1/2 left-full -translate-x-1/2 -translate-y-1/2 rounded-full"></div>
      </motion.div>
      {/* End Ring 3 */}
      <div className="container relative mt-16">
        <h1 className="text-8xl md:text-[168px] md:leading-none font-semibold tracking-tighter text-center bg-white bg-[radial-gradient(100%_100%_at_top_left,white,white,rgb(74,32,138,0.5))] text-transparent bg-clip-text">
          Grishinium ID
        </h1>
        <p className="text-lg md:text-xl text-white/70 mt-5 text-center max-w-xl mx-auto">
          Register your account for using full Grishinium Ecosystem
        </p>
        <p className="max-w-[52ch] mx-auto text-white/70 mb-8">
          Join the Grishinium Ecosystem and unlock your full potential in the world of decentralized applications. Create your digital identity today.
        </p>
        <Link href="/register">
          <button className="bg-gradient-to-b from-[#190d2e] to-[#4a208a] py-2 md:py-3 px-4 md:px-6 rounded-lg text-sm md:text-base font-medium relative shadow-[0px_0px_12px_#8c45ff] mb-4 md:mb-0">
            <div className="absolute inset-0">
              <div className="absolute border border-white/20 inset-0 rounded-lg [mask-image:linear-gradient(to_bottom,black,transparent)]"></div>
              <div className="absolute border border-white/40 inset-0 rounded-lg [mask-image:linear-gradient(to_top,black,transparent)]"></div>
              <div className="absolute inset-0 shadow-[0_0_10px_rgb(140,69,255,0.7)_inset] rounded-lg"></div>
            </div>
            <span>Join Grishinium</span>
          </button>
        </Link>
      </div>
    </motion.section>
  );
};
