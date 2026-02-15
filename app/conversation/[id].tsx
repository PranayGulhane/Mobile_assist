import React, { useState, useCallback, useEffect, useRef } from "react";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  TextInput,
  FlatList,
  Platform,
  useColorScheme,
  ActivityIndicator,
  KeyboardAvoidingView,
  Alert,
} from "react-native";
import { useLocalSearchParams, router } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons, Feather, MaterialCommunityIcons } from "@expo/vector-icons";
import { StatusBar } from "expo-status-bar";
import { LinearGradient } from "expo-linear-gradient";
import * as Haptics from "expo-haptics";
import { Audio } from "expo-av";
import { File } from "expo-file-system";
import { fetch as expoFetch } from "expo/fetch";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
  FadeIn,
  FadeInUp,
} from "react-native-reanimated";
import Colors from "@/constants/colors";
import { apiRequest, getApiUrl } from "@/lib/query-client";

interface Message {
  role: string;
  content: string;
  timestamp: string;
}

interface SentimentData {
  sentiment: string;
  confidence: number;
  details: string;
}

function WaveformBar({ index, isActive }: { index: number; isActive: boolean }) {
  const height = useSharedValue(8);

  useEffect(() => {
    if (isActive) {
      height.value = withRepeat(
        withSequence(
          withTiming(8 + Math.random() * 28, {
            duration: 200 + Math.random() * 300,
            easing: Easing.inOut(Easing.ease),
          }),
          withTiming(8 + Math.random() * 12, {
            duration: 200 + Math.random() * 300,
            easing: Easing.inOut(Easing.ease),
          })
        ),
        -1,
        true
      );
    } else {
      height.value = withTiming(8, { duration: 300 });
    }
  }, [isActive]);

  const animatedStyle = useAnimatedStyle(() => ({
    height: height.value,
  }));

  return (
    <Animated.View
      style={[
        styles.waveBar,
        animatedStyle,
        { backgroundColor: isActive ? "#FF3B30" : "#8E8E93" },
      ]}
    />
  );
}

function SentimentIndicator({ sentiment, isDark }: { sentiment: string; isDark: boolean }) {
  const theme = isDark ? Colors.dark : Colors.light;
  const color =
    sentiment === "negative"
      ? theme.sentimentNegative
      : sentiment === "mixed"
      ? theme.sentimentMixed
      : sentiment === "positive"
      ? theme.sentimentPositive
      : theme.sentimentNeutral;

  const label =
    sentiment === "negative"
      ? "Frustrated"
      : sentiment === "mixed"
      ? "Concerned"
      : sentiment === "positive"
      ? "Satisfied"
      : "Neutral";

  const icon =
    sentiment === "negative"
      ? "alert-circle"
      : sentiment === "mixed"
      ? "alert-triangle"
      : sentiment === "positive"
      ? "check-circle"
      : "minus-circle";

  return (
    <Animated.View
      entering={FadeIn.duration(400)}
      style={[styles.sentimentBadge, { backgroundColor: color + "18", borderColor: color + "40" }]}
    >
      <Feather name={icon as any} size={12} color={color} />
      <Text style={[styles.sentimentLabel, { color, fontFamily: "Inter_500Medium" }]}>
        {label}
      </Text>
    </Animated.View>
  );
}

function MessageBubble({ message, isDark, isLast }: { message: Message; isDark: boolean; isLast: boolean }) {
  const theme = isDark ? Colors.dark : Colors.light;
  const isUser = message.role === "user";

  return (
    <Animated.View
      entering={isLast ? FadeInUp.duration(400) : undefined}
      style={[
        styles.messageBubble,
        isUser ? styles.userBubble : styles.assistantBubble,
        {
          backgroundColor: isUser ? "#0A84FF" : theme.card,
          borderColor: isUser ? "transparent" : theme.border,
        },
      ]}
    >
      {!isUser && (
        <View style={styles.agentIcon}>
          <MaterialCommunityIcons name="headset" size={14} color="#0A84FF" />
        </View>
      )}
      <Text
        style={[
          styles.messageText,
          {
            color: isUser ? "#fff" : theme.text,
            fontFamily: "Inter_400Regular",
          },
        ]}
      >
        {message.content}
      </Text>
      <Text
        style={[
          styles.messageTime,
          {
            color: isUser ? "rgba(255,255,255,0.6)" : theme.textSecondary,
            fontFamily: "Inter_400Regular",
          },
        ]}
      >
        {new Date(message.timestamp).toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" })}
      </Text>
    </Animated.View>
  );
}

function TypingIndicator({ isDark }: { isDark: boolean }) {
  const theme = isDark ? Colors.dark : Colors.light;
  const dot1 = useSharedValue(0);
  const dot2 = useSharedValue(0);
  const dot3 = useSharedValue(0);

  useEffect(() => {
    dot1.value = withRepeat(
      withSequence(
        withTiming(-4, { duration: 300 }),
        withTiming(0, { duration: 300 })
      ),
      -1,
      false
    );
    setTimeout(() => {
      dot2.value = withRepeat(
        withSequence(
          withTiming(-4, { duration: 300 }),
          withTiming(0, { duration: 300 })
        ),
        -1,
        false
      );
    }, 150);
    setTimeout(() => {
      dot3.value = withRepeat(
        withSequence(
          withTiming(-4, { duration: 300 }),
          withTiming(0, { duration: 300 })
        ),
        -1,
        false
      );
    }, 300);
  }, []);

  const aStyle1 = useAnimatedStyle(() => ({ transform: [{ translateY: dot1.value }] }));
  const aStyle2 = useAnimatedStyle(() => ({ transform: [{ translateY: dot2.value }] }));
  const aStyle3 = useAnimatedStyle(() => ({ transform: [{ translateY: dot3.value }] }));

  return (
    <View style={[styles.typingContainer, { backgroundColor: theme.card, borderColor: theme.border }]}>
      <View style={styles.agentIcon}>
        <MaterialCommunityIcons name="headset" size={14} color="#0A84FF" />
      </View>
      <View style={styles.dotsRow}>
        <Animated.View style={[styles.typingDot, { backgroundColor: theme.textSecondary }, aStyle1]} />
        <Animated.View style={[styles.typingDot, { backgroundColor: theme.textSecondary }, aStyle2]} />
        <Animated.View style={[styles.typingDot, { backgroundColor: theme.textSecondary }, aStyle3]} />
      </View>
    </View>
  );
}

function RecordingTimer({ isRecording }: { isRecording: boolean }) {
  const [seconds, setSeconds] = useState(0);

  useEffect(() => {
    if (!isRecording) {
      setSeconds(0);
      return;
    }
    const interval = setInterval(() => setSeconds((s) => s + 1), 1000);
    return () => clearInterval(interval);
  }, [isRecording]);

  if (!isRecording) return null;

  const mins = Math.floor(seconds / 60);
  const secs = seconds % 60;

  return (
    <View style={styles.recordingTimerRow}>
      <View style={styles.recordingDot} />
      <Text style={styles.recordingTimerText}>
        {String(mins).padStart(2, "0")}:{String(secs).padStart(2, "0")}
      </Text>
    </View>
  );
}

export default function ConversationScreen() {
  const { id } = useLocalSearchParams<{ id: string }>();
  const insets = useSafeAreaInsets();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const theme = isDark ? Colors.dark : Colors.light;
  const [messages, setMessages] = useState<Message[]>([]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(true);
  const [isSending, setIsSending] = useState(false);
  const [isRecording, setIsRecording] = useState(false);
  const [isProcessingVoice, setIsProcessingVoice] = useState(false);
  const [showTextInput, setShowTextInput] = useState(false);
  const [sentiment, setSentiment] = useState("neutral");
  const [conversationStatus, setConversationStatus] = useState("active");
  const [isEscalated, setIsEscalated] = useState(false);
  const [permissionGranted, setPermissionGranted] = useState(false);
  const flatListRef = useRef<FlatList>(null);
  const recordingRef = useRef<Audio.Recording | null>(null);

  useEffect(() => {
    (async () => {
      const { status } = await Audio.requestPermissionsAsync();
      setPermissionGranted(status === "granted");
    })();
  }, []);

  const loadConversation = useCallback(async () => {
    try {
      const res = await apiRequest("GET", `/api/conversations/${id}`);
      const data = await res.json();
      setMessages(data.messages || []);
      setSentiment(data.sentiment || "neutral");
      setConversationStatus(data.status || "active");
      setIsEscalated(data.escalated || false);
    } catch (e) {
      console.log("Error loading conversation");
    } finally {
      setIsLoading(false);
    }
  }, [id]);

  useEffect(() => {
    loadConversation();
  }, [loadConversation]);

  const startRecording = async () => {
    if (!permissionGranted) {
      const { status } = await Audio.requestPermissionsAsync();
      if (status !== "granted") {
        Alert.alert("Microphone Access", "Please enable microphone access to use voice input.");
        return;
      }
      setPermissionGranted(true);
    }

    try {
      await Audio.setAudioModeAsync({
        allowsRecordingIOS: true,
        playsInSilentModeIOS: true,
      });

      const { recording } = await Audio.Recording.createAsync(
        Audio.RecordingOptionsPresets.HIGH_QUALITY
      );
      recordingRef.current = recording;
      setIsRecording(true);

      if (Platform.OS !== "web") {
        Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Medium);
      }
    } catch (err) {
      console.error("Failed to start recording", err);
      Alert.alert("Recording Error", "Could not start recording. Please try again.");
    }
  };

  const stopRecordingAndSend = async () => {
    if (!recordingRef.current) return;

    setIsRecording(false);
    setIsProcessingVoice(true);
    setIsSending(true);

    if (Platform.OS !== "web") {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }

    try {
      await recordingRef.current.stopAndUnloadAsync();
      const uri = recordingRef.current.getURI();
      recordingRef.current = null;

      if (!uri) {
        throw new Error("No recording URI");
      }

      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });

      const baseUrl = getApiUrl();
      const url = new URL(`/api/conversations/voice?conversation_id=${id}`, baseUrl);

      const formData = new FormData();

      if (Platform.OS === "web") {
        const response = await fetch(uri);
        const blob = await response.blob();
        formData.append("audio", blob, "recording.wav");
      } else {
        const file = new File(uri);
        formData.append("audio", file);
      }

      const res = await expoFetch(url.toString(), {
        method: "POST",
        body: formData,
        credentials: "include",
      });

      if (!res.ok) {
        const errorText = await res.text();
        throw new Error(`Server error: ${errorText}`);
      }

      const data = await res.json();

      if (data.error) {
        Alert.alert("Voice Error", data.error);
        setIsSending(false);
        setIsProcessingVoice(false);
        return;
      }

      if (data.conversation) {
        setMessages(data.conversation.messages || []);
        setSentiment(data.conversation.sentiment || "neutral");
        setConversationStatus(data.conversation.status || "active");
        setIsEscalated(data.conversation.escalated || false);
      }

      if (data.sentiment) {
        setSentiment(data.sentiment.sentiment || "neutral");
      }

      if (data.conversation?.escalated) {
        if (Platform.OS !== "web") {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
        }
      }
    } catch (e: any) {
      console.error("Voice processing error:", e);
      Alert.alert("Error", "Could not process your voice. Try speaking again or use text input.");
    } finally {
      setIsSending(false);
      setIsProcessingVoice(false);
    }
  };

  const cancelRecording = async () => {
    if (!recordingRef.current) return;
    try {
      await recordingRef.current.stopAndUnloadAsync();
      recordingRef.current = null;
      await Audio.setAudioModeAsync({ allowsRecordingIOS: false });
    } catch {}
    setIsRecording(false);
  };

  const sendMessage = async () => {
    if (!inputText.trim() || isSending) return;
    const text = inputText.trim();
    setInputText("");
    setIsSending(true);

    if (Platform.OS !== "web") {
      Haptics.impactAsync(Haptics.ImpactFeedbackStyle.Light);
    }

    const userMsg: Message = {
      role: "user",
      content: text,
      timestamp: new Date().toISOString(),
    };
    setMessages((prev) => [...prev, userMsg]);

    try {
      const res = await apiRequest("POST", "/api/conversations/message", {
        conversation_id: id,
        message: text,
      });
      const data = await res.json();

      if (data.conversation) {
        setMessages(data.conversation.messages || []);
        setSentiment(data.conversation.sentiment || "neutral");
        setConversationStatus(data.conversation.status || "active");
        setIsEscalated(data.conversation.escalated || false);
      }

      if (data.sentiment) {
        setSentiment(data.sentiment.sentiment || "neutral");
      }

      if (data.conversation?.escalated) {
        if (Platform.OS !== "web") {
          Haptics.notificationAsync(Haptics.NotificationFeedbackType.Warning);
        }
      }
    } catch (e) {
      Alert.alert("Error", "Failed to send message. Please try again.");
    } finally {
      setIsSending(false);
    }
  };

  const closeConversation = async () => {
    try {
      await apiRequest("POST", `/api/conversations/${id}/close`);
      if (Platform.OS !== "web") {
        Haptics.notificationAsync(Haptics.NotificationFeedbackType.Success);
      }
      router.back();
    } catch (e) {
      Alert.alert("Error", "Failed to close session.");
    }
  };

  const webTopInset = Platform.OS === "web" ? 67 : 0;
  const reversedMessages = [...messages].reverse();
  const isInputDisabled = conversationStatus === "closed" || isEscalated;

  if (isLoading) {
    return (
      <View style={[styles.container, styles.centered, { backgroundColor: theme.background }]}>
        <StatusBar style={isDark ? "light" : "dark"} />
        <ActivityIndicator color={theme.tint} size="large" />
      </View>
    );
  }

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={isDark ? "light" : "dark"} />

      <View style={[styles.topBar, { paddingTop: insets.top + 8 + webTopInset, backgroundColor: theme.card, borderBottomColor: theme.border }]}>
        <Pressable onPress={() => router.back()} style={styles.backButton} hitSlop={12}>
          <Ionicons name="chevron-back" size={24} color={theme.tint} />
        </Pressable>
        <View style={styles.topBarCenter}>
          <Text style={[styles.topBarTitle, { color: theme.text, fontFamily: "Inter_600SemiBold" }]}>
            Support Agent
          </Text>
          <SentimentIndicator sentiment={sentiment} isDark={isDark} />
        </View>
        {conversationStatus !== "closed" ? (
          <Pressable onPress={closeConversation} hitSlop={12}>
            <Feather name="x-circle" size={22} color={theme.textSecondary} />
          </Pressable>
        ) : (
          <View style={{ width: 22 }} />
        )}
      </View>

      {isEscalated && (
        <Animated.View entering={FadeIn.duration(400)} style={styles.escalationBanner}>
          <LinearGradient
            colors={["#FF3B30", "#FF6B35"]}
            start={{ x: 0, y: 0 }}
            end={{ x: 1, y: 0 }}
            style={styles.escalationGradient}
          >
            <Feather name="alert-triangle" size={14} color="#fff" />
            <Text style={[styles.escalationText, { fontFamily: "Inter_500Medium" }]}>
              Escalated - Human agent will connect within 30 min
            </Text>
          </LinearGradient>
        </Animated.View>
      )}

      <KeyboardAvoidingView
        style={styles.chatArea}
        behavior={Platform.OS === "ios" ? "padding" : "height"}
        keyboardVerticalOffset={0}
      >
        <FlatList
          ref={flatListRef}
          data={reversedMessages}
          keyExtractor={(_, index) => index.toString()}
          renderItem={({ item, index }) => (
            <MessageBubble message={item} isDark={isDark} isLast={index === 0} />
          )}
          contentContainerStyle={styles.messageList}
          showsVerticalScrollIndicator={false}
          inverted
          ListHeaderComponent={isSending ? <TypingIndicator isDark={isDark} /> : null}
        />

        {!isInputDisabled ? (
          <View
            style={[
              styles.inputArea,
              {
                backgroundColor: theme.card,
                borderTopColor: theme.border,
                paddingBottom: Platform.OS === "web" ? 34 : Math.max(insets.bottom, 12),
              },
            ]}
          >
            {isRecording ? (
              <View style={styles.recordingBar}>
                <View style={styles.waveformRow}>
                  {Array.from({ length: 24 }).map((_, i) => (
                    <WaveformBar key={i} index={i} isActive={true} />
                  ))}
                </View>
                <RecordingTimer isRecording={isRecording} />
                <View style={styles.recordingActions}>
                  <Pressable
                    onPress={cancelRecording}
                    style={({ pressed }) => [styles.cancelRecordBtn, { opacity: pressed ? 0.6 : 1 }]}
                  >
                    <Feather name="x" size={22} color="#FF3B30" />
                  </Pressable>
                  <Pressable
                    onPress={stopRecordingAndSend}
                    style={({ pressed }) => [styles.stopRecordBtn, { opacity: pressed ? 0.7 : 1 }]}
                  >
                    <LinearGradient
                      colors={["#0A84FF", "#30D5C8"]}
                      style={styles.stopRecordGradient}
                    >
                      <Ionicons name="send" size={20} color="#fff" />
                    </LinearGradient>
                  </Pressable>
                </View>
              </View>
            ) : showTextInput ? (
              <View style={styles.textInputBar}>
                <Pressable
                  onPress={() => setShowTextInput(false)}
                  style={({ pressed }) => [styles.switchModeBtn, { opacity: pressed ? 0.6 : 1 }]}
                >
                  <Ionicons name="mic" size={22} color={theme.tint} />
                </Pressable>
                <TextInput
                  style={[
                    styles.textInput,
                    {
                      backgroundColor: theme.background,
                      color: theme.text,
                      borderColor: theme.border,
                      fontFamily: "Inter_400Regular",
                    },
                  ]}
                  placeholder="Type your question..."
                  placeholderTextColor={theme.textSecondary}
                  value={inputText}
                  onChangeText={setInputText}
                  onSubmitEditing={sendMessage}
                  returnKeyType="send"
                  editable={!isSending}
                  multiline={false}
                  autoFocus
                />
                <Pressable
                  onPress={sendMessage}
                  disabled={!inputText.trim() || isSending}
                  style={({ pressed }) => [
                    styles.sendButton,
                    { opacity: !inputText.trim() || isSending ? 0.4 : pressed ? 0.7 : 1 },
                  ]}
                >
                  <LinearGradient colors={["#0A84FF", "#30D5C8"]} style={styles.sendGradient}>
                    <Ionicons name="send" size={18} color="#fff" />
                  </LinearGradient>
                </Pressable>
              </View>
            ) : (
              <View style={styles.voiceInputBar}>
                <View style={styles.voiceRow}>
                  <Pressable
                    onPress={() => setShowTextInput(true)}
                    style={({ pressed }) => [styles.switchModeBtn, { opacity: pressed ? 0.6 : 1 }]}
                  >
                    <Feather name="type" size={20} color={theme.textSecondary} />
                  </Pressable>

                  <Pressable
                    onPress={startRecording}
                    disabled={isSending}
                    style={({ pressed }) => [
                      styles.micButton,
                      { opacity: isSending ? 0.4 : pressed ? 0.8 : 1 },
                    ]}
                  >
                    <LinearGradient
                      colors={["#0A84FF", "#30D5C8"]}
                      style={styles.micGradient}
                    >
                      <Ionicons name="mic" size={28} color="#fff" />
                    </LinearGradient>
                  </Pressable>

                  <View style={{ width: 40 }} />
                </View>

                <Text style={[styles.voiceHint, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]}>
                  {isProcessingVoice ? "Processing..." : "Tap to speak"}
                </Text>
              </View>
            )}
          </View>
        ) : (
          <View
            style={[
              styles.closedBar,
              {
                backgroundColor: theme.card,
                borderTopColor: theme.border,
                paddingBottom: Platform.OS === "web" ? 34 : Math.max(insets.bottom, 12),
              },
            ]}
          >
            <Text style={[styles.closedText, { color: theme.textSecondary, fontFamily: "Inter_500Medium" }]}>
              {isEscalated
                ? "Session escalated to human agent"
                : "This session has ended"}
            </Text>
            <Pressable
              onPress={() => router.back()}
              style={({ pressed }) => [
                styles.backHomeButton,
                { opacity: pressed ? 0.8 : 1 },
              ]}
            >
              <Text style={[styles.backHomeText, { color: theme.tint, fontFamily: "Inter_600SemiBold" }]}>
                Back to Home
              </Text>
            </Pressable>
          </View>
        )}
      </KeyboardAvoidingView>
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  centered: {
    alignItems: "center",
    justifyContent: "center",
  },
  topBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 16,
    paddingBottom: 12,
    borderBottomWidth: 1,
    gap: 12,
  },
  backButton: {
    width: 32,
    height: 32,
    alignItems: "center",
    justifyContent: "center",
  },
  topBarCenter: {
    flex: 1,
    alignItems: "center",
    gap: 4,
  },
  topBarTitle: {
    fontSize: 16,
  },
  sentimentBadge: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
    paddingHorizontal: 8,
    paddingVertical: 2,
    borderRadius: 10,
    borderWidth: 1,
  },
  sentimentLabel: {
    fontSize: 11,
  },
  escalationBanner: {
    overflow: "hidden",
  },
  escalationGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 8,
    paddingVertical: 8,
    paddingHorizontal: 16,
  },
  escalationText: {
    color: "#fff",
    fontSize: 12,
  },
  chatArea: {
    flex: 1,
  },
  messageList: {
    paddingHorizontal: 16,
    paddingVertical: 8,
    gap: 8,
  },
  messageBubble: {
    maxWidth: "80%",
    padding: 12,
    borderRadius: 16,
    borderWidth: 1,
  },
  userBubble: {
    alignSelf: "flex-end",
    borderBottomRightRadius: 4,
  },
  assistantBubble: {
    alignSelf: "flex-start",
    borderBottomLeftRadius: 4,
  },
  agentIcon: {
    width: 22,
    height: 22,
    borderRadius: 11,
    backgroundColor: "#0A84FF15",
    alignItems: "center",
    justifyContent: "center",
    marginBottom: 4,
  },
  messageText: {
    fontSize: 15,
    lineHeight: 21,
  },
  messageTime: {
    fontSize: 10,
    marginTop: 4,
    alignSelf: "flex-end",
  },
  typingContainer: {
    alignSelf: "flex-start",
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    padding: 12,
    borderRadius: 16,
    borderBottomLeftRadius: 4,
    borderWidth: 1,
  },
  dotsRow: {
    flexDirection: "row",
    gap: 4,
  },
  typingDot: {
    width: 6,
    height: 6,
    borderRadius: 3,
  },
  inputArea: {
    borderTopWidth: 1,
    paddingTop: 10,
  },
  voiceInputBar: {
    alignItems: "center",
    paddingHorizontal: 16,
    gap: 8,
  },
  voiceRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 16,
  },
  micButton: {
    width: 64,
    height: 64,
    borderRadius: 32,
    overflow: "hidden",
    shadowColor: "#0A84FF",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 8,
    elevation: 6,
  },
  micGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  voiceHint: {
    fontSize: 12,
    marginBottom: 4,
  },
  switchModeBtn: {
    width: 40,
    height: 40,
    alignItems: "center",
    justifyContent: "center",
  },
  recordingBar: {
    alignItems: "center",
    paddingHorizontal: 16,
    gap: 12,
  },
  waveformRow: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    gap: 2,
    height: 44,
  },
  waveBar: {
    width: 3,
    borderRadius: 2,
    minHeight: 4,
  },
  recordingTimerRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 6,
  },
  recordingDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
    backgroundColor: "#FF3B30",
  },
  recordingTimerText: {
    fontSize: 14,
    fontFamily: "Inter_500Medium",
    color: "#FF3B30",
  },
  recordingActions: {
    flexDirection: "row",
    alignItems: "center",
    gap: 24,
    marginBottom: 4,
  },
  cancelRecordBtn: {
    width: 44,
    height: 44,
    borderRadius: 22,
    backgroundColor: "#FF3B3015",
    alignItems: "center",
    justifyContent: "center",
  },
  stopRecordBtn: {
    width: 52,
    height: 52,
    borderRadius: 26,
    overflow: "hidden",
  },
  stopRecordGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  textInputBar: {
    flexDirection: "row",
    alignItems: "center",
    paddingHorizontal: 12,
    gap: 8,
  },
  textInput: {
    flex: 1,
    height: 42,
    borderRadius: 21,
    paddingHorizontal: 16,
    fontSize: 15,
    borderWidth: 1,
  },
  sendButton: {
    width: 42,
    height: 42,
    borderRadius: 21,
    overflow: "hidden",
  },
  sendGradient: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
  },
  closedBar: {
    alignItems: "center",
    paddingHorizontal: 16,
    paddingTop: 12,
    borderTopWidth: 1,
    gap: 8,
  },
  closedText: {
    fontSize: 13,
  },
  backHomeButton: {
    paddingVertical: 8,
    paddingHorizontal: 20,
  },
  backHomeText: {
    fontSize: 15,
  },
});
