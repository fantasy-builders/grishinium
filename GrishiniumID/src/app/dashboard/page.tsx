"use client";
import { useState, useEffect } from "react";
import { motion } from "framer-motion";
import { Header } from "@/sections/Header";
import { Footer } from "@/sections/Footer";
import { useUser, Badge } from "@/hooks/useUser";
import { useRouter } from "next/navigation";

export default function Dashboard() {
  const { user, loading, logout } = useUser();
  const router = useRouter();
  const [activeTab, setActiveTab] = useState<'profile' | 'badges' | 'certifications'>('profile');

  // If not authenticated and not loading, redirect to home
  useEffect(() => {
    if (!loading && !user) {
      router.push('/');
    }
  }, [loading, user, router]);

  // Generate sample badges based on user skills
  useEffect(() => {
    if (user && user.skills && user.skills.length > 0 && (!user.badges || user.badges.length === 0)) {
      // This would normally happen on the server, but we're doing it client-side for demo
      const sampleBadges: Badge[] = user.skills.slice(0, 3).map((skill, index) => ({
        id: `skill-${index + 1}`,
        name: `${skill} Developer`,
        description: `Verified ${skill} development skills`,
        category: "skill",
        image: `/badge-${skill.toLowerCase().replace(/\s/g, '-')}.png`,
        date: new Date().toISOString()
      }));
      
      // Add a participation badge
      sampleBadges.push({
        id: "participation-1",
        name: "DAO Participant",
        description: "Active participant in Grishinium DAO governance",
        category: "participation",
        image: "/badge-dao.png",
        date: new Date().toISOString()
      });
    }
  }, [user]);

  const getReputationColor = (rep: number) => {
    if (rep >= 900) return "#FFD700"; // gold
    if (rep >= 750) return "#9370DB"; // purple
    if (rep >= 500) return "#1E90FF"; // blue
    if (rep >= 250) return "#32CD32"; // green
    return "#808080"; // gray
  };

  const getBadgeColorByCategory = (category: string) => {
    switch (category) {
      case "skill":
        return "bg-blue-600";
      case "achievement":
        return "bg-purple-600";
      case "participation":
        return "bg-green-600";
      case "certification":
        return "bg-amber-600";
      default:
        return "bg-gray-600";
    }
  };

  if (loading) {
    return (
      <main>
        <Header />
        <div className="min-h-screen flex justify-center items-center">
          <div className="animate-spin rounded-full h-16 w-16 border-t-4 border-b-4 border-purple-500"></div>
        </div>
        <Footer />
      </main>
    );
  }

  if (!user) {
    return (
      <main>
        <Header />
        <section className="py-20 min-h-screen flex flex-col items-center justify-center relative">
          <div className="container">
            <div className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-8 rounded-2xl shadow-lg mx-auto max-w-lg text-center">
              <h2 className="text-2xl font-bold text-white mb-4">No Profile Found</h2>
              <p className="text-gray-300 mb-6">
                You don't have a Grishinium ID yet. Create one to start building your on-chain reputation.
              </p>
              <a
                href="/register"
                className="py-2 px-6 rounded-lg bg-gradient-to-b from-[#190d2e] to-[#4a208a] shadow-[0px_0px_12px_#8c45ff] inline-block"
              >
                Create Grishinium ID
              </a>
            </div>
          </div>
        </section>
        <Footer />
      </main>
    );
  }

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
          {/* Profile Header */}
          <div className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-6 md:p-8 rounded-2xl shadow-lg backdrop-blur-sm mb-8">
            <div className="flex flex-col md:flex-row items-center md:items-start gap-6">
              {/* Avatar */}
              <div className="relative">
                <div className="w-24 h-24 md:w-32 md:h-32 rounded-full bg-gradient-to-b from-[#8c45ff] to-[#4a208a] flex items-center justify-center text-3xl font-bold text-white">
                  {user.name.charAt(0).toUpperCase()}
                </div>
                <div className="absolute -bottom-2 -right-2 bg-[#4a208a] rounded-full p-1.5 border-2 border-[#190d2e]">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-5 w-5 text-white" viewBox="0 0 20 20" fill="currentColor">
                    <path fillRule="evenodd" d="M6.267 3.455a3.066 3.066 0 001.745-.723 3.066 3.066 0 013.976 0 3.066 3.066 0 001.745.723 3.066 3.066 0 012.812 2.812c.051.643.304 1.254.723 1.745a3.066 3.066 0 010 3.976 3.066 3.066 0 00-.723 1.745 3.066 3.066 0 01-2.812 2.812 3.066 3.066 0 00-1.745.723 3.066 3.066 0 01-3.976 0 3.066 3.066 0 00-1.745-.723 3.066 3.066 0 01-2.812-2.812 3.066 3.066 0 00-.723-1.745 3.066 3.066 0 010-3.976 3.066 3.066 0 00.723-1.745 3.066 3.066 0 012.812-2.812zm7.44 5.252a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                  </svg>
                </div>
              </div>
              
              {/* Profile Info */}
              <div className="flex-1 text-center md:text-left">
                <h1 className="text-2xl md:text-3xl font-bold text-white mb-2">
                  {user.name}
                </h1>
                <p className="text-gray-400 mb-3 text-sm break-all">
                  {user.address}
                </p>
                <p className="text-gray-300 mb-4">
                  {user.bio || `${user.name}'s Profile`}
                </p>
                
                <div className="flex flex-wrap gap-2 justify-center md:justify-start mb-4">
                  <span className="px-3 py-1 bg-[#4a208a] rounded-full text-sm text-white">
                    {user.level} Level
                  </span>
                  <span className="px-3 py-1 bg-[#0e0024] border border-[#4a208a]/50 rounded-full text-sm text-white">
                    {user.reputation} Reputation
                  </span>
                  <span className="px-3 py-1 bg-[#0e0024] border border-[#4a208a]/50 rounded-full text-sm text-white">
                    {user.stakeAmount} GRI Staked
                  </span>
                </div>
                
                {user.github && (
                  <a 
                    href={`https://${user.github}`}
                    target="_blank"
                    rel="noopener noreferrer"
                    className="inline-flex items-center text-[#8c45ff] hover:text-white transition-colors"
                  >
                    <svg className="w-4 h-4 mr-1" fill="currentColor" viewBox="0 0 24 24">
                      <path d="M12 0c-6.626 0-12 5.373-12 12 0 5.302 3.438 9.8 8.207 11.387.599.111.793-.261.793-.577v-2.234c-3.338.726-4.033-1.416-4.033-1.416-.546-1.387-1.333-1.756-1.333-1.756-1.089-.745.083-.729.083-.729 1.205.084 1.839 1.237 1.839 1.237 1.07 1.834 2.807 1.304 3.492.997.107-.775.418-1.305.762-1.604-2.665-.305-5.467-1.334-5.467-5.931 0-1.311.469-2.381 1.236-3.221-.124-.303-.535-1.524.117-3.176 0 0 1.008-.322 3.301 1.23.957-.266 1.983-.399 3.003-.404 1.02.005 2.047.138 3.006.404 2.291-1.552 3.297-1.23 3.297-1.23.653 1.653.242 2.874.118 3.176.77.84 1.235 1.911 1.235 3.221 0 4.609-2.807 5.624-5.479 5.921.43.372.823 1.102.823 2.222v3.293c0 .319.192.694.801.576 4.765-1.589 8.199-6.086 8.199-11.386 0-6.627-5.373-12-12-12z"/>
                    </svg>
                    GitHub Profile
                  </a>
                )}

                {/* Buttons */}
                <div className="mt-4 flex flex-wrap gap-2 justify-center md:justify-start">
                  <button
                    className="px-4 py-1.5 bg-[#0e0024] border border-[#4a208a]/50 rounded-lg text-sm hover:bg-[#190d2e] transition-colors"
                    onClick={() => router.push("/verify-skills")}
                  >
                    Verify More Skills
                  </button>
                  <button
                    onClick={logout}
                    className="px-4 py-1.5 bg-red-900/50 border border-red-800/50 rounded-lg text-sm hover:bg-red-900/70 transition-colors"
                  >
                    Logout
                  </button>
                </div>
              </div>
            </div>
          </div>
          
          {/* Tabs */}
          <div className="mb-6">
            <div className="flex border-b border-[#4a208a]/30">
              <button
                className={`px-6 py-3 text-sm font-medium ${
                  activeTab === 'profile'
                    ? 'text-[#8c45ff] border-b-2 border-[#8c45ff]'
                    : 'text-gray-400 hover:text-white'
                }`}
                onClick={() => setActiveTab('profile')}
              >
                Profile
              </button>
              <button
                className={`px-6 py-3 text-sm font-medium ${
                  activeTab === 'badges'
                    ? 'text-[#8c45ff] border-b-2 border-[#8c45ff]'
                    : 'text-gray-400 hover:text-white'
                }`}
                onClick={() => setActiveTab('badges')}
              >
                Badges
              </button>
              <button
                className={`px-6 py-3 text-sm font-medium ${
                  activeTab === 'certifications'
                    ? 'text-[#8c45ff] border-b-2 border-[#8c45ff]'
                    : 'text-gray-400 hover:text-white'
                }`}
                onClick={() => setActiveTab('certifications')}
              >
                Certifications
              </button>
            </div>
          </div>
          
          {/* Tab Content */}
          <div className="bg-[#190d2e]/80 border border-[#4a208a]/50 p-6 rounded-2xl shadow-lg backdrop-blur-sm">
            {activeTab === 'profile' && (
              <div>
                <h2 className="text-xl font-semibold text-white mb-6">Account Information</h2>
                
                <div className="grid grid-cols-1 md:grid-cols-2 gap-6 mb-8">
                  <div className="bg-[#0e0024] border border-[#4a208a]/30 p-5 rounded-xl">
                    <h3 className="text-lg font-medium text-white mb-4">Personal Details</h3>
                    <div className="space-y-3">
                      <div>
                        <p className="text-sm text-gray-400">Display Name</p>
                        <p className="text-white">{user.name}</p>
                      </div>
                      {user.email && (
                        <div>
                          <p className="text-sm text-gray-400">Email</p>
                          <p className="text-white">{user.email}</p>
                        </div>
                      )}
                      {user.github && (
                        <div>
                          <p className="text-sm text-gray-400">GitHub</p>
                          <p className="text-white">{user.github}</p>
                        </div>
                      )}
                      {user.registrationDate && (
                        <div>
                          <p className="text-sm text-gray-400">Member Since</p>
                          <p className="text-white">{new Date(user.registrationDate).toLocaleDateString()}</p>
                        </div>
                      )}
                    </div>
                  </div>
                  
                  <div className="bg-[#0e0024] border border-[#4a208a]/30 p-5 rounded-xl">
                    <h3 className="text-lg font-medium text-white mb-4">Skills & Expertise</h3>
                    <div className="flex flex-wrap gap-2">
                      {user.skills && user.skills.length > 0 ? (
                        user.skills.map((skill, index) => (
                          <span 
                            key={index}
                            className="px-3 py-1 bg-[#4a208a]/40 rounded-full text-sm text-white"
                          >
                            {skill}
                          </span>
                        ))
                      ) : (
                        <p className="text-gray-400">No skills added yet</p>
                      )}
                    </div>
                  </div>
                </div>
                
                <div className="bg-[#0e0024] border border-[#4a208a]/30 p-5 rounded-xl mb-6">
                  <h3 className="text-lg font-medium text-white mb-4">Blockchain Information</h3>
                  <div className="space-y-3">
                    <div>
                      <p className="text-sm text-gray-400">Wallet Address</p>
                      <p className="text-white break-all">{user.address}</p>
                    </div>
                    <div>
                      <p className="text-sm text-gray-400">GRI Token Stake</p>
                      <p className="text-white">{user.stakeAmount} GRI</p>
                    </div>
                    {user.txHash && (
                      <div>
                        <p className="text-sm text-gray-400">Registration Transaction</p>
                        <p className="text-[#8c45ff] break-all">{user.txHash}</p>
                      </div>
                    )}
                  </div>
                </div>
                
                <div className="bg-[#0e0024] border border-[#4a208a]/30 p-5 rounded-xl">
                  <h3 className="text-lg font-medium text-white mb-4">Reputation & Trust Level</h3>
                  <div className="w-full bg-gray-800 rounded-full h-4 mb-4">
                    <div 
                      className="bg-[#8c45ff] h-4 rounded-full" 
                      style={{ 
                        width: `${Math.min(100, (user.reputation || 0) / 10)}%`,
                        backgroundColor: getReputationColor(user.reputation || 0) 
                      }}
                    ></div>
                  </div>
                  <div className="flex justify-between text-sm mb-6">
                    <span className="text-gray-400">0</span>
                    <span className="text-gray-400">250</span>
                    <span className="text-gray-400">500</span>
                    <span className="text-gray-400">750</span>
                    <span className="text-gray-400">1000</span>
                  </div>
                  <div className="text-center">
                    <p className="text-white font-medium">{user.reputation} / 1000</p>
                    <p className="text-sm text-gray-400">
                      Current Level: {user.level}
                    </p>
                  </div>
                </div>
              </div>
            )}
            
            {activeTab === 'badges' && (
              <div>
                <div className="flex justify-between items-center mb-6">
                  <h2 className="text-xl font-semibold text-white">Earned Badges</h2>
                  <p className="text-sm text-gray-400">
                    {(user.badges?.length || 0)} Total Badges
                  </p>
                </div>
                
                {(!user.badges || user.badges.length === 0) ? (
                  <div className="bg-[#0e0024] border border-[#4a208a]/30 p-8 rounded-xl text-center">
                    <div className="mb-4">
                      <svg xmlns="http://www.w3.org/2000/svg" className="h-12 w-12 mx-auto text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                        <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M19.428 15.428a2 2 0 00-1.022-.547l-2.387-.477a6 6 0 00-3.86.517l-.318.158a6 6 0 01-3.86.517L6.05 15.21a2 2 0 00-1.806.547M8 4h8l-1 1v5.172a2 2 0 00.586 1.414l5 5c1.26 1.26.367 3.414-1.415 3.414H4.828c-1.782 0-2.674-2.154-1.414-3.414l5-5A2 2 0 009 10.172V5L8 4z" />
                      </svg>
                    </div>
                    <h3 className="text-lg font-medium text-white mb-2">No Badges Yet</h3>
                    <p className="text-gray-400 mb-6">
                      Complete skill verification tests or participate in ecosystem activities to earn badges.
                    </p>
                    <button 
                      onClick={() => router.push("/verify-skills")}
                      className="px-4 py-2 bg-[#4a208a] rounded-lg text-sm hover:bg-[#4a208a]/80 transition-colors"
                    >
                      Verify Skills
                    </button>
                  </div>
                ) : (
                  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
                    {user.badges.map((badge) => (
                      <div 
                        key={badge.id}
                        className="bg-[#0e0024] border border-[#4a208a]/30 rounded-xl overflow-hidden"
                      >
                        <div className={`${getBadgeColorByCategory(badge.category)} p-4 flex items-center gap-3`}>
                          <div className="w-10 h-10 bg-black/30 rounded-full flex items-center justify-center">
                            <svg xmlns="http://www.w3.org/2000/svg" className="h-6 w-6 text-white" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                              <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M9 12l2 2 4-4m5.618-4.016A11.955 11.955 0 0112 2.944a11.955 11.955 0 01-8.618 3.04A12.02 12.02 0 003 9c0 5.591 3.824 10.29 9 11.622 5.176-1.332 9-6.03 9-11.622 0-1.042-.133-2.052-.382-3.016z" />
                            </svg>
                          </div>
                          <div>
                            <p className="text-white font-medium">{badge.name}</p>
                            <p className="text-xs text-white/70">
                              {badge.category.charAt(0).toUpperCase() + badge.category.slice(1)} Badge
                            </p>
                          </div>
                        </div>
                        <div className="p-4">
                          <p className="text-sm text-gray-300 mb-4">
                            {badge.description}
                          </p>
                          <p className="text-xs text-gray-400">
                            Earned on {new Date(badge.date).toLocaleDateString()}
                          </p>
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}
            
            {activeTab === 'certifications' && (
              <div className="text-center p-8">
                <div className="mb-6">
                  <svg xmlns="http://www.w3.org/2000/svg" className="h-16 w-16 mx-auto text-gray-500" fill="none" viewBox="0 0 24 24" stroke="currentColor">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={1.5} d="M9 12l2 2 4-4M7.835 4.697a3.42 3.42 0 001.946-.806 3.42 3.42 0 014.438 0 3.42 3.42 0 001.946.806 3.42 3.42 0 013.138 3.138 3.42 3.42 0 00.806 1.946 3.42 3.42 0 010 4.438 3.42 3.42 0 00-.806 1.946 3.42 3.42 0 01-3.138 3.138 3.42 3.42 0 00-1.946.806 3.42 3.42 0 01-4.438 0 3.42 3.42 0 00-1.946-.806 3.42 3.42 0 01-3.138-3.138 3.42 3.42 0 00-.806-1.946 3.42 3.42 0 010-4.438 3.42 3.42 0 00.806-1.946 3.42 3.42 0 013.138-3.138z" />
                  </svg>
                </div>
                <h3 className="text-lg font-medium text-white mb-2">
                  Certifications Coming Soon
                </h3>
                <p className="text-gray-400 max-w-md mx-auto mb-6">
                  The Grishinium certification system is under development. 
                  Soon you'll be able to prove your expertise with certified skill assessments.
                </p>
                <button 
                  className="px-4 py-2 bg-[#4a208a]/50 rounded-lg text-sm cursor-not-allowed"
                  disabled
                >
                  Get Notified
                </button>
              </div>
            )}
          </div>
        </motion.div>
      </section>
      <Footer />
    </main>
  );
} 