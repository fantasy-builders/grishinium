"use client";
import { createContext, useContext, useState, useEffect, ReactNode } from "react";

export interface UserProfile {
  name: string;
  email: string;
  github: string;
  skills: string[];
  stakeAmount: number;
  address?: string;
  bio?: string;
  reputation?: number;
  level?: string;
  badges?: Badge[];
  txHash?: string;
  registrationDate?: string;
}

export interface Badge {
  id: string;
  name: string;
  description: string;
  category: "skill" | "achievement" | "participation" | "certification";
  image: string;
  date: string;
}

interface UserContextType {
  user: UserProfile | null;
  isAuthenticated: boolean;
  registerUser: (userData: UserProfile) => void;
  updateUser: (userData: Partial<UserProfile>) => void;
  logout: () => void;
  loading: boolean;
}

const UserContext = createContext<UserContextType | undefined>(undefined);

export const UserProvider = ({ children }: { children: ReactNode }) => {
  const [user, setUser] = useState<UserProfile | null>(null);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    // Load user data from localStorage on initial load
    const loadUser = () => {
      try {
        const storedUser = localStorage.getItem("grishiniumUser");
        if (storedUser) {
          setUser(JSON.parse(storedUser));
        }
      } catch (error) {
        console.error("Error loading user data:", error);
      } finally {
        setLoading(false);
      }
    };

    loadUser();
  }, []);

  const registerUser = (userData: UserProfile) => {
    // Generate a random blockchain address for demo purposes
    const address = "0x" + Math.random().toString(16).substring(2, 42);
    
    // Set default values for new users
    const newUser: UserProfile = {
      ...userData,
      address,
      reputation: 100,
      level: "Beginner",
      bio: userData.bio || `${userData.name}'s Profile`,
      badges: [],
      registrationDate: new Date().toISOString(),
    };
    
    // Save user to localStorage
    localStorage.setItem("grishiniumUser", JSON.stringify(newUser));
    setUser(newUser);
  };

  const updateUser = (userData: Partial<UserProfile>) => {
    if (!user) return;
    
    const updatedUser = { ...user, ...userData };
    localStorage.setItem("grishiniumUser", JSON.stringify(updatedUser));
    setUser(updatedUser);
  };

  const logout = () => {
    localStorage.removeItem("grishiniumUser");
    setUser(null);
  };

  return (
    <UserContext.Provider 
      value={{ 
        user, 
        isAuthenticated: !!user, 
        registerUser, 
        updateUser, 
        logout,
        loading
      }}
    >
      {children}
    </UserContext.Provider>
  );
};

export const useUser = () => {
  const context = useContext(UserContext);
  if (context === undefined) {
    throw new Error("useUser must be used within a UserProvider");
  }
  return context;
}; 