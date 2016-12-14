function getUserData(username, reload) {
  // Hide error message if it's visible
  $("#error").hide();

  var target = $SCRIPT_ROOT + "/stats/" + username;
  var params = {refresh: reload};
  $.getJSON(target, params,
    function(data) {
      display(data);
    })
    .fail(function(jqxhr, textStatus, error) {
      var msg = textStatus + " " + error;
      displayError(msg);
    });
  }

function display(data) {
  if ("error" in data) {
    displayError(data.error);
    return;
  }

  var info = [
    data.refreshed,
    data.account_created,
    data.oldest_post_date,
    data.total_karma,
    data.words_per_post,
    data.karma_per_word
  ];

  var postcount = "based on the " + data.postcount + " most recent posts";
  $("#user h2").text(postcount);

  // Add basic user info
  $("#info").find("strong").each(function(i) {
    $(this).text(info[i]);
  });

  // Clear graphs
  $("svg").remove();

  // Draw plot for subreddit stats
  if ("subreddits" in data) {
    barplot(data.subreddits);
    // Add average score under barplot
    $("#barplot + h2").text("Average post score is " + data.avgscore);
  }

  // Draw plot for post stats
  if ("posts" in data) {
    activityPlot(data.posts);
  }

  if ("daydata" in data && "hourdata" in data) {
    radarchart(data.daydata, data.hourdata);
  }

  if ("wordcount" in data) {
    wordcloud(data.wordcount);
  }
}

function displayError(msg) {
  var element = $("#error");
  $("> h1", element).text(msg);
  element.show();
}
