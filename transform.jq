def parse_twitter_date:
  strptime("%a %b %d %H:%M:%S +0000 %Y") | strftime("%Y-%m-%dT%H:%M:%S+00:00");

.data.user.result.timeline.timeline.instructions[0].entries[]
| select(.content.entryType == "TimelineTimelineItem")
| .content.itemContent.tweet_results.result
| {
    # We store these as strings as `jq` represents numbers as 64-bit floats, so
    # anything larger than 2^53-1 (≈ 9.007e15) can’t be represented exactly,
    # and these identifiers can be higher.
    id: .rest_id,
    user_id: .core.user_results.result.rest_id,

    media_array: [
      .legacy.extended_entities.media[]?
      | select(.type == "photo" or .type == "video" or .type == "animated_gif")
      | if .type == "video" or .type == "animated_gif" then
          (.media_url_https // .video_info.thumbnail_url)
        else
          .media_url_https
        end
    ],
    tweet: "https://twitter.com/\(.core.user_results.result.legacy.screen_name)/status/\(.rest_id)",
    name: .core.user_results.result.legacy.name,
    created_at: (.legacy.created_at | parse_twitter_date),
    full_text: .legacy.full_text,
    is_quote_status: (if .legacy.is_quote_status then 1 else 0 end),
    favorite_count: .legacy.favorite_count,
    favorited: (if .legacy.favorited then 1 else 0 end),
    retweeted: (if .legacy.retweeted then 1 else 0 end),
    lang: .legacy.lang,
    possibly_sensitive: (if .legacy.possibly_sensitive then 1 else 0 end),
    retweeted_status: (.legacy.retweeted_status_result.result | if . then . else null end),
    quoted_status: (
      if .quoted_status_result.result then
        .quoted_status_result.result.rest_id
      else
        null
      end
    ),
    thumbnail: (
      .legacy.extended_entities.media[0]
      | if . then
          if .type == "video" or .type == "animated_gif" then
            (.media_url_https // .video_info.thumbnail_url)
          else
            .media_url_https
          end
        else
          null
        end
    )
}
