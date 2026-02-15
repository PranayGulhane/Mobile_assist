import React, { useState, useCallback, useRef, useEffect } from "react";
import {
  StyleSheet,
  Text,
  View,
  Pressable,
  FlatList,
  Platform,
  useColorScheme,
  ActivityIndicator,
  Alert,
} from "react-native";
import { router, useFocusEffect } from "expo-router";
import { useSafeAreaInsets } from "react-native-safe-area-context";
import { Ionicons, MaterialCommunityIcons, Feather } from "@expo/vector-icons";
import { StatusBar } from "expo-status-bar";
import { LinearGradient } from "expo-linear-gradient";
import Animated, {
  useSharedValue,
  useAnimatedStyle,
  withRepeat,
  withTiming,
  withSequence,
  Easing,
  FadeInDown,
  FadeIn,
} from "react-native-reanimated";
import Colors from "@/constants/colors";
import { apiRequest } from "@/lib/query-client";

interface ConversationItem {
  id: string;
  title: string;
  status: string;
  sentiment: string;
  ticket_type: string;
  resolution_status: string;
  created_at: string;
  escalated: boolean;
  summary?: string;
}

function PulsingOrb() {
  const scale = useSharedValue(1);
  const opacity = useSharedValue(0.6);

  useEffect(() => {
    scale.value = withRepeat(
      withSequence(
        withTiming(1.2, { duration: 1500, easing: Easing.inOut(Easing.ease) }),
        withTiming(1, { duration: 1500, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      false
    );
    opacity.value = withRepeat(
      withSequence(
        withTiming(0.3, { duration: 1500, easing: Easing.inOut(Easing.ease) }),
        withTiming(0.6, { duration: 1500, easing: Easing.inOut(Easing.ease) })
      ),
      -1,
      false
    );
  }, []);

  const animatedStyle = useAnimatedStyle(() => ({
    transform: [{ scale: scale.value }],
    opacity: opacity.value,
  }));

  return (
    <Animated.View style={[styles.orbContainer, animatedStyle]}>
      <LinearGradient
        colors={["#0A84FF", "#30D5C8"]}
        start={{ x: 0, y: 0 }}
        end={{ x: 1, y: 1 }}
        style={styles.orb}
      />
    </Animated.View>
  );
}

function ConversationCard({ item, isDark }: { item: ConversationItem; isDark: boolean }) {
  const theme = isDark ? Colors.dark : Colors.light;
  const date = new Date(item.created_at);
  const timeStr = date.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
  const dateStr = date.toLocaleDateString([], { month: "short", day: "numeric" });

  const sentimentColor =
    item.sentiment === "negative"
      ? theme.sentimentNegative
      : item.sentiment === "mixed"
      ? theme.sentimentMixed
      : theme.sentimentPositive;

  const statusColor =
    item.status === "escalated"
      ? theme.statusEscalated
      : item.status === "active"
      ? theme.statusActive
      : theme.statusClosed;

  return (
    <Pressable
      onPress={() => router.push({ pathname: "/conversation/[id]", params: { id: item.id } })}
      style={({ pressed }) => [
        styles.card,
        {
          backgroundColor: theme.card,
          borderColor: theme.border,
          opacity: pressed ? 0.85 : 1,
          transform: [{ scale: pressed ? 0.98 : 1 }],
        },
      ]}
    >
      <View style={styles.cardHeader}>
        <View style={styles.cardTitleRow}>
          <View style={[styles.sentimentDot, { backgroundColor: sentimentColor }]} />
          <Text style={[styles.cardTitle, { color: theme.text, fontFamily: "Inter_600SemiBold" }]} numberOfLines={1}>
            {item.title || "Support Session"}
          </Text>
        </View>
        <View style={[styles.statusBadge, { backgroundColor: statusColor + "20", borderColor: statusColor }]}>
          <Text style={[styles.statusText, { color: statusColor, fontFamily: "Inter_500Medium" }]}>
            {item.resolution_status === "human_followup_required"
              ? "Escalated"
              : item.resolution_status === "ai_resolved"
              ? "Resolved"
              : "Active"}
          </Text>
        </View>
      </View>
      {item.summary ? (
        <Text style={[styles.cardSummary, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]} numberOfLines={2}>
          {item.summary}
        </Text>
      ) : null}
      <View style={styles.cardFooter}>
        <View style={styles.cardMeta}>
          <Ionicons name="time-outline" size={12} color={theme.textSecondary} />
          <Text style={[styles.cardMetaText, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]}>
            {dateStr} at {timeStr}
          </Text>
        </View>
        <View style={styles.cardMeta}>
          <Ionicons name="ticket-outline" size={12} color={theme.textSecondary} />
          <Text style={[styles.cardMetaText, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]}>
            {item.ticket_type === "complaint" ? "Complaint" : "Info"}
          </Text>
        </View>
      </View>
    </Pressable>
  );
}

export default function HomeScreen() {
  const insets = useSafeAreaInsets();
  const colorScheme = useColorScheme();
  const isDark = colorScheme === "dark";
  const theme = isDark ? Colors.dark : Colors.light;
  const [conversations, setConversations] = useState<ConversationItem[]>([]);
  const [isStarting, setIsStarting] = useState(false);
  const [isLoading, setIsLoading] = useState(true);

  const loadConversations = useCallback(async () => {
    try {
      const res = await apiRequest("GET", "/api/conversations");
      const data = await res.json();
      setConversations(data);
    } catch (e) {
      console.log("Could not load conversations");
    } finally {
      setIsLoading(false);
    }
  }, []);

  useFocusEffect(
    useCallback(() => {
      loadConversations();
    }, [loadConversations])
  );

  const startConversation = async () => {
    setIsStarting(true);
    try {
      const res = await apiRequest("POST", "/api/conversations/start");
      const data = await res.json();
      router.push({ pathname: "/conversation/[id]", params: { id: data.id } });
    } catch (e) {
      Alert.alert("Connection Error", "Unable to reach support service. Please try again.");
    } finally {
      setIsStarting(false);
    }
  };

  const webTopInset = Platform.OS === "web" ? 67 : 0;

  return (
    <View style={[styles.container, { backgroundColor: theme.background }]}>
      <StatusBar style={isDark ? "light" : "dark"} />

      <View style={[styles.header, { paddingTop: insets.top + 12 + webTopInset }]}>
        <Animated.View entering={FadeIn.duration(600)}>
          <Text style={[styles.appTitle, { color: theme.text, fontFamily: "Inter_700Bold" }]}>
            Assist Link
          </Text>
          <Text style={[styles.appSubtitle, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]}>
            Intelligent Voice Support
          </Text>
        </Animated.View>
      </View>

      <Animated.View
        entering={FadeInDown.duration(800).delay(200)}
        style={styles.heroSection}
      >
        <View style={styles.heroCenter}>
          <PulsingOrb />
          <Pressable
            onPress={startConversation}
            disabled={isStarting}
            style={({ pressed }) => [
              styles.talkButton,
              {
                opacity: pressed ? 0.9 : 1,
                transform: [{ scale: pressed ? 0.95 : 1 }],
              },
            ]}
          >
            <LinearGradient
              colors={["#0A84FF", "#30D5C8"]}
              start={{ x: 0, y: 0 }}
              end={{ x: 1, y: 1 }}
              style={styles.talkButtonGradient}
            >
              {isStarting ? (
                <ActivityIndicator color="#fff" size="small" />
              ) : (
                <>
                  <MaterialCommunityIcons name="headset" size={28} color="#fff" />
                  <Text style={[styles.talkButtonText, { fontFamily: "Inter_600SemiBold" }]}>
                    Talk to Support
                  </Text>
                </>
              )}
            </LinearGradient>
          </Pressable>
          <Text style={[styles.heroHint, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]}>
            Tap to speak with your AI support agent
          </Text>
        </View>
      </Animated.View>

      <Animated.View
        entering={FadeInDown.duration(800).delay(400)}
        style={styles.historySection}
      >
        <View style={styles.sectionHeader}>
          <Text style={[styles.sectionTitle, { color: theme.text, fontFamily: "Inter_600SemiBold" }]}>
            Recent Sessions
          </Text>
          {conversations.length > 0 && (
            <View style={styles.countBadge}>
              <Text style={[styles.countText, { fontFamily: "Inter_500Medium" }]}>{conversations.length}</Text>
            </View>
          )}
        </View>

        {isLoading ? (
          <View style={styles.emptyState}>
            <ActivityIndicator color={theme.tint} />
          </View>
        ) : conversations.length === 0 ? (
          <View style={styles.emptyState}>
            <Feather name="message-circle" size={40} color={theme.textSecondary} />
            <Text style={[styles.emptyTitle, { color: theme.textSecondary, fontFamily: "Inter_500Medium" }]}>
              No conversations yet
            </Text>
            <Text style={[styles.emptySubtitle, { color: theme.textSecondary, fontFamily: "Inter_400Regular" }]}>
              Tap "Talk to Support" to get started
            </Text>
          </View>
        ) : (
          <FlatList
            data={conversations}
            keyExtractor={(item) => item.id}
            renderItem={({ item }) => <ConversationCard item={item} isDark={isDark} />}
            contentContainerStyle={styles.listContent}
            showsVerticalScrollIndicator={false}
          />
        )}
      </Animated.View>

      {Platform.OS === "web" && <View style={{ height: 34 }} />}
    </View>
  );
}

const styles = StyleSheet.create({
  container: {
    flex: 1,
  },
  header: {
    paddingHorizontal: 24,
    paddingBottom: 8,
  },
  appTitle: {
    fontSize: 28,
    letterSpacing: -0.5,
  },
  appSubtitle: {
    fontSize: 14,
    marginTop: 2,
  },
  heroSection: {
    paddingHorizontal: 24,
    paddingVertical: 28,
    alignItems: "center",
  },
  heroCenter: {
    alignItems: "center",
    gap: 16,
  },
  orbContainer: {
    width: 100,
    height: 100,
    borderRadius: 50,
    marginBottom: 4,
  },
  orb: {
    width: 100,
    height: 100,
    borderRadius: 50,
  },
  talkButton: {
    borderRadius: 16,
    overflow: "hidden",
    shadowColor: "#0A84FF",
    shadowOffset: { width: 0, height: 4 },
    shadowOpacity: 0.3,
    shadowRadius: 12,
    elevation: 8,
  },
  talkButtonGradient: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "center",
    paddingHorizontal: 32,
    paddingVertical: 16,
    gap: 10,
  },
  talkButtonText: {
    color: "#fff",
    fontSize: 17,
  },
  heroHint: {
    fontSize: 13,
  },
  historySection: {
    flex: 1,
    paddingHorizontal: 24,
  },
  sectionHeader: {
    flexDirection: "row",
    alignItems: "center",
    justifyContent: "space-between",
    marginBottom: 12,
  },
  sectionTitle: {
    fontSize: 18,
  },
  countBadge: {
    backgroundColor: "#0A84FF",
    borderRadius: 10,
    paddingHorizontal: 8,
    paddingVertical: 2,
  },
  countText: {
    color: "#fff",
    fontSize: 12,
  },
  listContent: {
    paddingBottom: 40,
    gap: 10,
  },
  card: {
    borderRadius: 14,
    padding: 16,
    borderWidth: 1,
  },
  cardHeader: {
    flexDirection: "row",
    justifyContent: "space-between",
    alignItems: "center",
    marginBottom: 6,
  },
  cardTitleRow: {
    flexDirection: "row",
    alignItems: "center",
    gap: 8,
    flex: 1,
  },
  sentimentDot: {
    width: 8,
    height: 8,
    borderRadius: 4,
  },
  cardTitle: {
    fontSize: 15,
    flex: 1,
  },
  statusBadge: {
    borderRadius: 8,
    paddingHorizontal: 8,
    paddingVertical: 3,
    borderWidth: 1,
  },
  statusText: {
    fontSize: 11,
  },
  cardSummary: {
    fontSize: 13,
    lineHeight: 18,
    marginBottom: 8,
  },
  cardFooter: {
    flexDirection: "row",
    gap: 16,
  },
  cardMeta: {
    flexDirection: "row",
    alignItems: "center",
    gap: 4,
  },
  cardMetaText: {
    fontSize: 11,
  },
  emptyState: {
    flex: 1,
    alignItems: "center",
    justifyContent: "center",
    gap: 10,
    paddingVertical: 40,
  },
  emptyTitle: {
    fontSize: 16,
    marginTop: 4,
  },
  emptySubtitle: {
    fontSize: 13,
  },
});
