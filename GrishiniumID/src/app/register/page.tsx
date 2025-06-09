"use client";
import { useState } from "react";
import { motion } from "framer-motion";
import { Header } from "@/sections/Header";
import { Footer } from "@/sections/Footer";
import { useUser, UserProfile } from "@/hooks/useUser";
import { useRouter } from "next/navigation";

// Имитация функции взаимодействия с блокчейном для создания Grishinium ID
const createGrishiniumID = async (data: UserProfile): Promise<{ success: boolean; txHash?: string; error?: string }> => {
  // В реальном приложении здесь был бы вызов смарт-контракта через Web3.js/ethers.js
  // Например: await contract.methods.createID(data.name, data.github, data.skills).send({from: account, value: stakeAmountWei});
  
  // Имитация ответа для демонстрации
  return new Promise((resolve) => {
    setTimeout(() => {
      // Имитация успешного создания ID
      resolve({
        success: true,
        txHash: "0x" + Math.random().toString(16).substring(2, 42)
      });
    }, 2000);
  });
};

const availableSkills = [
  "Solidity", "Rust", "Web3.js", "React", "Node.js", "Blockchain Security", 
  "Smart Contract Auditing", "DeFi", "NFT", "DAO Governance"
];

export default function Register() {
  const { registerUser, isAuthenticated } = useUser();
  const router = useRouter();
  const [step, setStep] = useState<number>(1);
  const [formData, setFormData] = useState<UserProfile>({
    name: "",
    email: "",
    github: "",
    skills: [],
    stakeAmount: 100, // минимальная сумма стейкинга
  });
  const [loading, setLoading] = useState<boolean>(false);
  const [error, setError] = useState<string | null>(null);
  const [success, setSuccess] = useState<boolean>(false);
  const [txHash, setTxHash] = useState<string | null>(null);

  // Redirect to dashboard if already authenticated
  if (isAuthenticated && !loading && !success) {
    router.push('/dashboard');
  }

  const handleInputChange = (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement>) => {
    const { name, value } = e.target;
    setFormData((prev) => ({
      ...prev,
      [name]: value,
    }));
  };

  const handleSkillToggle = (skill: string) => {
    setFormData((prev) => {
      const skills = [...prev.skills];
      if (skills.includes(skill)) {
        return { ...prev, skills: skills.filter(s => s !== skill) };
      } else {
        return { ...prev, skills: [...skills, skill] };
      }
    });
  };

  const handleNextStep = () => {
    setStep(prev => prev + 1);
  };

  const handlePrevStep = () => {
    setStep(prev => prev - 1);
  };

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    setLoading(true);
    setError(null);

    try {
      const result = await createGrishiniumID(formData);
      
      if (result.success) {
        // Register user in our context/local storage
        const userData = {
          ...formData,
          txHash: result.txHash,
        };
        
        registerUser(userData);
        
        setSuccess(true);
        setTxHash(result.txHash || null);
        setStep(4); // Переход к экрану успеха
      } else {
        setError(result.error || "Failed to create Grishinium ID");
      }
    } catch (err) {
      setError("An unexpected error occurred");
      console.error(err);
    } finally {
      setLoading(false);
    }
  };

  return (
    <main>
      <Header />
      <section className="py-20 min-h-screen flex flex-col items-center justify-center relative">
        <div className="absolute inset-0 bg-[radial-gradient(50%_50%_at_center_center,rgb(140,69,255,0.2)_0%,rgb(14,0,36)_70%)]"></div>
        
        <motion.div 
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ duration: 0.5 }}
          className="container relative z-10 max-w-2xl mx-auto"
        >
          <h1 className="text-4xl md:text-5xl font-bold text-center bg-gradient-to-r from-white to-purple-300 text-transparent bg-clip-text mb-6">
            Create Your Grishinium ID
          </h1>
          
          {!success ? (
            <div className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-8 rounded-2xl shadow-lg backdrop-blur-sm">
              <div className="flex justify-between mb-8">
                {[1, 2, 3].map((num) => (
                  <div 
                    key={num}
                    className={`flex items-center justify-center w-10 h-10 rounded-full ${
                      num <= step ? "bg-[#4a208a] text-white" : "bg-gray-700 text-gray-400"
                    }`}
                  >
                    {num}
                  </div>
                ))}
              </div>
              
              {step === 1 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-6"
                >
                  <h2 className="text-2xl font-semibold text-white mb-4">Personal Information</h2>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Display Name</label>
                    <input
                      type="text"
                      name="name"
                      value={formData.name}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 bg-[#0e0024] border border-[#4a208a]/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#8c45ff]/50"
                      placeholder="Your name on Grishinium platform"
                      required
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Email Address</label>
                    <input
                      type="email"
                      name="email"
                      value={formData.email}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 bg-[#0e0024] border border-[#4a208a]/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#8c45ff]/50"
                      placeholder="For notifications (optional)"
                    />
                  </div>
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">GitHub Profile</label>
                    <input
                      type="text"
                      name="github"
                      value={formData.github}
                      onChange={handleInputChange}
                      className="w-full px-4 py-2 bg-[#0e0024] border border-[#4a208a]/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#8c45ff]/50"
                      placeholder="github.com/yourusername"
                    />
                  </div>
                  <div className="flex justify-end">
                    <button
                      type="button"
                      onClick={handleNextStep}
                      disabled={!formData.name}
                      className={`py-2 px-6 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff] ${!formData.name ? 'opacity-50 cursor-not-allowed' : ''}`}
                    >
                      Next
                    </button>
                  </div>
                </motion.div>
              )}
              
              {step === 2 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-6"
                >
                  <h2 className="text-2xl font-semibold text-white mb-4">Skills & Expertise</h2>
                  <p className="text-sm text-gray-300 mb-4">
                    Select your skills to earn relevant badges and get discovered by companies
                  </p>
                  <div className="flex flex-wrap gap-3">
                    {availableSkills.map((skill) => (
                      <button
                        key={skill}
                        type="button"
                        onClick={() => handleSkillToggle(skill)}
                        className={`py-2 px-4 rounded-full text-sm ${
                          formData.skills.includes(skill)
                            ? "bg-[#4a208a] text-white"
                            : "bg-[#0e0024] text-gray-300 border border-[#4a208a]/50"
                        }`}
                      >
                        {skill}
                      </button>
                    ))}
                  </div>
                  <div className="flex justify-between">
                    <button
                      type="button"
                      onClick={handlePrevStep}
                      className="py-2 px-6 rounded-lg bg-[#0e0024] border border-[#4a208a]/50 text-gray-300"
                    >
                      Back
                    </button>
                    <button
                      type="button"
                      onClick={handleNextStep}
                      className="py-2 px-6 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff]"
                    >
                      Next
                    </button>
                  </div>
                </motion.div>
              )}
              
              {step === 3 && (
                <motion.div
                  initial={{ opacity: 0 }}
                  animate={{ opacity: 1 }}
                  className="space-y-6"
                >
                  <h2 className="text-2xl font-semibold text-white mb-4">Stake GRI Tokens</h2>
                  <p className="text-sm text-gray-300 mb-4">
                    Staking GRI tokens increases your profile's trust level and reputation. 
                    The minimum stake is 100 GRI.
                  </p>
                  
                  <div>
                    <label className="block text-sm font-medium text-gray-300 mb-1">Stake Amount (GRI)</label>
                    <input
                      type="number"
                      name="stakeAmount"
                      value={formData.stakeAmount}
                      onChange={handleInputChange}
                      min={100}
                      className="w-full px-4 py-2 bg-[#0e0024] border border-[#4a208a]/50 rounded-lg text-white focus:outline-none focus:ring-2 focus:ring-[#8c45ff]/50"
                    />
                  </div>
                  
                  <div className="mt-10">
                    <h3 className="text-xl font-semibold text-white mb-4">Review Your Information</h3>
                    <div className="space-y-2 bg-[#0e0024] border border-[#4a208a]/30 p-4 rounded-lg mb-6">
                      <p>
                        <span className="text-gray-400">Name:</span> <span className="text-white">{formData.name}</span>
                      </p>
                      {formData.email && (
                        <p>
                          <span className="text-gray-400">Email:</span> <span className="text-white">{formData.email}</span>
                        </p>
                      )}
                      {formData.github && (
                        <p>
                          <span className="text-gray-400">GitHub:</span> <span className="text-white">{formData.github}</span>
                        </p>
                      )}
                      <p>
                        <span className="text-gray-400">Skills:</span>{" "}
                        <span className="text-white">
                          {formData.skills.length > 0 ? formData.skills.join(", ") : "None selected"}
                        </span>
                      </p>
                      <p>
                        <span className="text-gray-400">Stake Amount:</span> <span className="text-white">{formData.stakeAmount} GRI</span>
                      </p>
                    </div>
                  </div>
                  
                  <div className="flex justify-between items-center">
                    <button
                      type="button"
                      onClick={handlePrevStep}
                      className="py-2 px-6 rounded-lg bg-[#0e0024] border border-[#4a208a]/50 text-gray-300"
                    >
                      Back
                    </button>
                    <div>
                      {error && (
                        <p className="text-red-500 text-sm mb-2">{error}</p>
                      )}
                      <button
                        type="button"
                        onClick={handleSubmit}
                        disabled={loading}
                        className="py-2 px-6 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff] relative"
                      >
                        {loading ? (
                          <span className="flex items-center">
                            <svg className="animate-spin -ml-1 mr-2 h-4 w-4 text-white" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
                              <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4"></circle>
                              <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"></path>
                            </svg>
                            Processing...
                          </span>
                        ) : (
                          "Create Grishinium ID"
                        )}
                      </button>
                    </div>
                  </div>
                </motion.div>
              )}
            </div>
          ) : (
            <motion.div 
              initial={{ opacity: 0, scale: 0.9 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-8 rounded-2xl shadow-lg backdrop-blur-sm text-center"
            >
              <div className="inline-flex items-center justify-center w-16 h-16 rounded-full bg-green-500 mb-6">
                <svg xmlns="http://www.w3.org/2000/svg" className="h-8 w-8 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M5 13l4 4L19 7" />
                </svg>
              </div>
              <h2 className="text-2xl font-bold text-white mb-4">Grishinium ID Created!</h2>
              <p className="text-gray-300 mb-6">
                Your Grishinium ID has been successfully created and recorded on the blockchain.
              </p>
              
              {txHash && (
                <div className="bg-[#0e0024] border border-[#4a208a]/30 p-3 rounded-lg mb-6 overflow-auto">
                  <p className="text-sm text-gray-400 mb-1">Transaction Hash:</p>
                  <p className="text-xs text-[#8c45ff] break-all">{txHash}</p>
                </div>
              )}
              
              <div className="mt-8">
                <button
                  type="button"
                  onClick={() => router.push('/dashboard')}
                  className="py-2 px-6 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff]"
                >
                  Go to Dashboard
                </button>
              </div>
            </motion.div>
          )}
        </motion.div>
      </section>
      <Footer />
    </main>
  );
} 