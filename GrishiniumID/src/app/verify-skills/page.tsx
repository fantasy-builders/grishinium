"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Header } from "@/sections/Header";
import { Footer } from "@/sections/Footer";
import { useUser, Badge } from "@/hooks/useUser";
import { useRouter } from "next/navigation";

interface SkillTest {
  id: string;
  name: string;
  description: string;
  level: string;
  duration: string;
  questions: number;
}

const availableTests: SkillTest[] = [
  {
    id: "solidity-basic",
    name: "Solidity Basics",
    description: "Fundamentals of Solidity programming language",
    level: "Beginner",
    duration: "30 min",
    questions: 15
  },
  {
    id: "web3-dev",
    name: "Web3.js Development",
    description: "Building frontend dApps with Web3.js",
    level: "Intermediate",
    duration: "45 min",
    questions: 20
  },
  {
    id: "defi-concepts",
    name: "DeFi Concepts",
    description: "Understanding decentralized finance protocols",
    level: "Intermediate",
    duration: "40 min",
    questions: 18
  },
  {
    id: "smart-contract-security",
    name: "Smart Contract Security",
    description: "Identifying vulnerabilities in smart contracts",
    level: "Advanced",
    duration: "60 min",
    questions: 25
  }
];

export default function VerifySkills() {
  const { user, updateUser } = useUser();
  const router = useRouter();
  const [selectedTest, setSelectedTest] = useState<SkillTest | null>(null);
  const [loading, setLoading] = useState(false);
  const [testCompleted, setTestCompleted] = useState(false);
  const [badgeAwarded, setBadgeAwarded] = useState<Badge | null>(null);

  // Redirect to home if not logged in
  if (!user) {
    typeof window !== 'undefined' && router.push('/register');
    return null;
  }

  const startTest = (test: SkillTest) => {
    setSelectedTest(test);
    window.scrollTo(0, 0);
  };

  const simulateTestCompletion = async () => {
    setLoading(true);
    
    // Simulate test completion
    await new Promise(resolve => setTimeout(resolve, 2000));
    
    // Generate a badge for the completed test
    const newBadge: Badge = {
      id: `skill-${selectedTest?.id || 'test'}-${Date.now()}`,
      name: `${selectedTest?.name || 'Skill'} Badge`,
      description: `Successfully verified knowledge in ${selectedTest?.name || 'blockchain technology'}`,
      category: "skill",
      image: `/badge-${selectedTest?.id || 'skill'}.png`,
      date: new Date().toISOString()
    };
    
    // Add badge to user profile
    const updatedBadges = [...(user.badges || []), newBadge];
    const updatedReputation = (user.reputation || 100) + 50; // Increase reputation
    
    // Update user level based on new reputation
    let updatedLevel = user.level || "Beginner";
    if (updatedReputation >= 900) updatedLevel = "Legendary";
    else if (updatedReputation >= 750) updatedLevel = "Expert";
    else if (updatedReputation >= 500) updatedLevel = "Advanced";
    else if (updatedReputation >= 250) updatedLevel = "Intermediate";
    
    // Update user profile
    updateUser({
      badges: updatedBadges,
      reputation: updatedReputation,
      level: updatedLevel
    });
    
    // Set state to show completion
    setTestCompleted(true);
    setBadgeAwarded(newBadge);
    setLoading(false);
  };

  const resetTest = () => {
    setSelectedTest(null);
    setTestCompleted(false);
    setBadgeAwarded(null);
  };

  return (
    <main>
      <Header />
      <section className="py-12 min-h-screen relative">
        <div className="absolute inset-0 bg-[radial-gradient(50%_50%_at_center_center,rgb(140,69,255,0.1)_0%,rgb(14,0,36)_70%)]"></div>
        
        <motion.div 
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          className="container relative z-10"
        >
          <div className="max-w-4xl mx-auto">
          <h1 className="text-4xl md:text-5xl font-bold text-center bg-gradient-to-r from-white to-purple-300 text-transparent bg-clip-text mb-6">
            Verify Your Skills
          </h1>
            <p className="text-gray-300 text-center mb-12 max-w-2xl mx-auto">
              Complete skill verification tests to earn badges and increase your reputation on Grishinium.
              Each verified skill is recorded on the blockchain as part of your decentralized identity.
            </p>
            
            {!selectedTest ? (
              <div className="grid grid-cols-1 md:grid-cols-2 gap-6">
                {availableTests.map((test) => (
                  <div 
                    key={test.id}
                    className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-6 rounded-2xl shadow-lg backdrop-blur-sm hover:border-[#4a208a] transition-colors"
                  >
                    <h3 className="text-xl font-semibold text-white mb-2">{test.name}</h3>
                    <div className="flex gap-3 mb-4">
                      <span className="px-2 py-1 bg-[#0e0024] border border-[#4a208a]/50 rounded-full text-xs text-white">
                        {test.level}
                      </span>
                      <span className="px-2 py-1 bg-[#0e0024] border border-[#4a208a]/50 rounded-full text-xs text-white">
                        {test.duration}
                      </span>
                      <span className="px-2 py-1 bg-[#0e0024] border border-[#4a208a]/50 rounded-full text-xs text-white">
                        {test.questions} questions
                      </span>
                  </div>
                    <p className="text-sm text-gray-300 mb-6">
                      {test.description}
                    </p>
                    <button
                      onClick={() => startTest(test)}
                      className="w-full py-2 px-4 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff] text-white text-sm hover:shadow-[0px_0px_16px_#8c45ff] transition-shadow"
                    >
                      Start Test
                    </button>
                  </div>
                ))}
                </div>
            ) : (
              <div className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-8 rounded-2xl shadow-lg backdrop-blur-sm">
                {!testCompleted ? (
                  <>
                    <div className="flex justify-between items-center mb-8">
                      <h2 className="text-2xl font-semibold text-white">{selectedTest.name} Test</h2>
                      <button
                        onClick={resetTest}
                        className="text-gray-400 hover:text-white"
                      >
                        Cancel
                      </button>
                    </div>
                    
                    <div className="mb-8">
                      <div className="bg-[#0e0024] border border-[#4a208a]/30 p-5 rounded-xl mb-6">
                        <h3 className="text-lg font-medium text-white mb-4">Test Information</h3>
                        <ul className="space-y-2">
                          <li className="flex items-center text-gray-300">
                            <span className="w-32 text-gray-400">Level:</span> 
                            {selectedTest.level}
                          </li>
                          <li className="flex items-center text-gray-300">
                            <span className="w-32 text-gray-400">Duration:</span> 
                            {selectedTest.duration}
                          </li>
                          <li className="flex items-center text-gray-300">
                            <span className="w-32 text-gray-400">Questions:</span> 
                            {selectedTest.questions}
                          </li>
                          <li className="flex items-center text-gray-300">
                            <span className="w-32 text-gray-400">Passing Score:</span> 
                            70%
                          </li>
                          <li className="flex items-center text-gray-300">
                            <span className="w-32 text-gray-400">Reputation:</span> 
                            +50 points on completion
                          </li>
                        </ul>
                      </div>
                      
                      <div className="bg-[#0e0024] border border-[#4a208a]/30 p-5 rounded-xl">
                        <h3 className="text-lg font-medium text-white mb-4">Instructions</h3>
                        <ul className="list-disc pl-5 space-y-2 text-gray-300 text-sm">
                          <li>You will have {selectedTest.duration} to complete this test.</li>
                          <li>Answer all {selectedTest.questions} questions to the best of your ability.</li>
                          <li>You need to score at least 70% to pass and earn a badge.</li>
                          <li>Once you start, you cannot pause or exit the test.</li>
                          <li>For demonstration purposes, this test simulation will automatically complete successfully.</li>
                        </ul>
                      </div>
                    </div>
                    
                    <div className="flex justify-center">
                      <button
                        onClick={simulateTestCompletion}
                        disabled={loading}
                        className="py-3 px-8 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff] text-white flex items-center justify-center min-w-[200px]"
                      >
                        {loading ? (
                          <span className="flex items-center">
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                          </svg>
                            Completing Test...
                          </span>
                        ) : (
                          "Start Test"
                        )}
                      </button>
                    </div>
                  </>
                ) : (
                  <motion.div 
                    initial={{ opacity: 0, scale: 0.9 }}
                    animate={{ opacity: 1, scale: 1 }}
                    className="text-center"
                  >
                    <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500 mb-6">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                    </svg>
                    </div>
                    <h2 className="text-2xl font-bold text-white mb-4">Test Completed!</h2>
                    <p className="text-gray-300 mb-8">
                      Congratulations! You've successfully completed the {selectedTest.name} test.
                      A new badge has been added to your profile.
                    </p>
                    
                    {badgeAwarded && (
                      <div className="bg-[#0e0024] border border-[#4a208a]/30 rounded-xl overflow-hidden max-w-sm mx-auto mb-8">
                        <div className="bg-blue-600 p-4 flex items-center gap-3">
                          <div className="w-10 h-10 bg-black/30 rounded-full flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-white font-medium">{badgeAwarded.name}</p>
                            <p className="text-xs text-white/70">
                              Skill Badge
                            </p>
                          </div>
                        </div>
                        <div className="p-4">
                          <p className="text-sm text-gray-300 mb-4">
                            {badgeAwarded.description}
                          </p>
                          <p className="text-xs text-gray-400">
                            Earned on {new Date(badgeAwarded.date).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    )}
                    
                    <div className="flex flex-wrap gap-4 justify-center">
                      <button
                        onClick={resetTest}
                        className="py-2 px-6 rounded-lg bg-[#0e0024] border border-[#4a208a]/50 text-gray-300 hover:bg-[#190d2e] transition-colors"
                      >
                        Take Another Test
                      </button>
                      <button
                        onClick={() => router.push('/dashboard')}
                        className="py-2 px-6 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff]"
                      >
                        Go to Dashboard
                      </button>
                  </div>
                  </motion.div>
                )}
              </div>
            )}
          </div>
        </motion.div>
      </section>
      <Footer />
    </main>
  );
} 